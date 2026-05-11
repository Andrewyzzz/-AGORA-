"""
Governance module — handles market proposals and voting.
"""
import time
from datetime import datetime, timedelta, timezone
from agents.modules.decision_module import DecisionModule
from agents.modules.execution_module import ExecutionModule
from agents.modules.data_module import DataModule
from bridge.polymarket import PolymarketBridge

_polymarket = PolymarketBridge()


class GovernanceModule:
    def __init__(
        self,
        decision: DecisionModule,
        execution: ExecutionModule,
        data: DataModule,
        agent_id: str,
        logger,
    ):
        self.decision = decision
        self.execution = execution
        self.data = data
        self.agent_id = agent_id
        self.log = logger

    @staticmethod
    def _extract_keywords(text: str) -> set[str]:
        """Extract meaningful keywords for dedup check."""
        stop = {"will","the","a","an","by","in","on","of","to","is","be","for",
                "before","after","end","year","2026","2027","officially","formally"}
        return {w.lower() for w in text.split() if len(w) > 3 and w.lower() not in stop}

    def _is_duplicate(self, question: str, existing_questions: list[str], threshold: float = 0.5) -> bool:
        """Return True if question is too similar to an existing market."""
        new_kw = self._extract_keywords(question)
        if not new_kw:
            return False
        for eq in existing_questions:
            existing_kw = self._extract_keywords(eq)
            if not existing_kw:
                continue
            overlap = len(new_kw & existing_kw) / max(len(new_kw | existing_kw), 1)
            if overlap >= threshold:
                return True
        return False

    def maybe_propose(self) -> bool:
        """Scan news + Polymarket and submit a market proposal if a good opportunity exists."""
        now = datetime.now(timezone.utc)
        today = now.strftime("%B %d, %Y")
        min_resolution = now + timedelta(days=3)

        news = self.data.get_recent_news(20)
        news_with_date = [f"[TODAY IS {today} — only propose markets about FUTURE events]"] + news

        # ── Inject Polymarket reference markets ──────────────────────────────
        pm_markets = []
        try:
            pm_markets = _polymarket.get_recent_markets(limit=10)
        except Exception:
            pass
        if pm_markets:
            pm_lines = ["[POLYMARKET RECENTLY LISTED MARKETS — use as inspiration, do NOT copy verbatim]"]
            for m in pm_markets:
                price_str = f"YES={m['yes_price']*100:.0f}%" if m['yes_price'] else "YES=?"
                pm_lines.append(f"  [{m['end_date']}] {price_str} vol=${m['volume']:,.0f} | {m['question']}")
            news_with_date = pm_lines + [""] + news_with_date

        existing = self.execution.get_all_markets()
        existing_questions = []
        for addr in existing[:20]:
            try:
                info = self.execution.get_market_info(addr)
                existing_questions.append(info["question"])
            except Exception:
                pass

        proposal = self.decision.decide_proposal(news_with_date, existing_questions)
        if not proposal or not proposal.question:
            self.log(f"[{self.agent_id}] No proposal opportunity found.")
            return False

        # ── Hard date validation: resolution must be at least 3 days in future ──
        resolution_dt = now + timedelta(days=proposal.resolution_days)
        if resolution_dt < min_resolution:
            self.log(
                f"[{self.agent_id}] Proposal rejected (resolves too soon: "
                f"{resolution_dt.strftime('%Y-%m-%d')}): '{proposal.question[:50]}'"
            )
            return False

        # ── Dedup check ───────────────────────────────────────────────────────
        if self._is_duplicate(proposal.question, existing_questions):
            self.log(f"[{self.agent_id}] Proposal rejected (duplicate): '{proposal.question[:50]}'")
            return False

        resolution_ts = int(
            (datetime.now(timezone.utc) + timedelta(days=proposal.resolution_days)).timestamp()
        )

        try:
            result = self.execution.propose_market(
                question=proposal.question,
                resolution_criteria=proposal.resolution_criteria,
                resolution_timestamp=resolution_ts,
                liquidity_parameter=proposal.liquidity_parameter,
                reasoning=proposal.reasoning,
            )
            self.log(
                f"[{self.agent_id}] Proposed market: '{proposal.question[:60]}' "
                f"tx={result['tx_hash'][:12]}..."
            )
            return True
        except Exception as e:
            self.log(f"[{self.agent_id}] Proposal failed: {e}")
            return False

    def vote_on_pending(self) -> int:
        """Vote on all pending proposals the agent hasn't voted on yet."""
        count = self.execution.get_proposal_count()
        votes_cast = 0

        for proposal_id in range(count):
            try:
                proposal = self.execution.governance.functions.proposals(proposal_id).call()
                # proposal tuple: proposer, question, resolutionCriteria, resolutionTimestamp,
                #                  liquidityParameter, votesFor, votesAgainst, votingDeadline,
                #                  executed, createdMarket, proposerReasoning
                voting_deadline = proposal[7]
                if int(time.time()) > voting_deadline:
                    continue
                if self.execution.governance.functions.hasVoted(
                    proposal_id, self.execution.wallet.address
                ).call():
                    continue

                # Enrich with Polymarket reference price if available
                proposer_reasoning = proposal[10]
                try:
                    pm_ref = _polymarket.search_market(proposal[1][:50])
                    if pm_ref and pm_ref.yes_price is not None:
                        proposer_reasoning += (
                            f"\n[Polymarket reference: similar market prices YES at "
                            f"{pm_ref.yes_price*100:.0f}% — volume ${pm_ref.volume:,.0f}]"
                        )
                except Exception:
                    pass

                vote_decision = self.decision.decide_vote(
                    question=proposal[1],
                    resolution_criteria=proposal[2],
                    proposer_reasoning=proposer_reasoning,
                )
                result = self.execution.vote(
                    proposal_id=proposal_id,
                    support=vote_decision.support,
                    reasoning=vote_decision.reasoning,
                )
                action = "FOR" if vote_decision.support else "AGAINST"
                self.log(
                    f"[{self.agent_id}] Voted {action} proposal #{proposal_id}: "
                    f"'{proposal[1][:50]}' tx={result['tx_hash'][:12]}..."
                )
                votes_cast += 1
            except Exception as e:
                self.log(f"[{self.agent_id}] Vote error on #{proposal_id}: {e}")

        return votes_cast

    def try_execute_approved(self) -> list[str]:
        """Execute proposals that passed voting. Only checks recent proposals to avoid spam."""
        count = self.execution.get_proposal_count()
        new_markets = []

        # Only scan the most recent 20 proposals — old ones either executed or failed
        start = max(0, count - 20)
        for proposal_id in range(start, count):
            try:
                proposal = self.execution.governance.functions.proposals(proposal_id).call()
                executed = proposal[8]
                voting_deadline = proposal[7]
                votes_for = proposal[5]
                votes_against = proposal[6]
                quorum = self.execution.governance.functions.quorum().call()

                if executed:
                    continue
                if int(time.time()) <= voting_deadline:
                    continue
                if votes_for <= votes_against:
                    continue
                if votes_for + votes_against < quorum:
                    continue  # skip without logging — quorum not met is expected

                result = self.execution.execute_proposal(proposal_id)
                market_addr = result["receipt"]["logs"][0]["address"] if result["receipt"].get("logs") else ""
                self.log(f"[{self.agent_id}] Executed proposal #{proposal_id} → market {market_addr}")
                new_markets.append(market_addr)
            except Exception as e:
                self.log(f"[{self.agent_id}] Execute error on #{proposal_id}: {e}")

        return new_markets
