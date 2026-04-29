"""
Governance module — handles market proposals and voting.
"""
import time
from datetime import datetime, timedelta, timezone
from agents.modules.decision_module import DecisionModule
from agents.modules.execution_module import ExecutionModule
from agents.modules.data_module import DataModule


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

    def maybe_propose(self) -> bool:
        """Scan news and submit a market proposal if a good opportunity exists."""
        news = self.data.get_recent_news(20)
        existing = self.execution.get_all_markets()
        existing_questions = []
        for addr in existing[:10]:
            try:
                info = self.execution.get_market_info(addr)
                existing_questions.append(info["question"])
            except Exception:
                pass

        proposal = self.decision.decide_proposal(news, existing_questions)
        if not proposal or not proposal.question:
            self.log(f"[{self.agent_id}] No proposal opportunity found.")
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

                vote_decision = self.decision.decide_vote(
                    question=proposal[1],
                    resolution_criteria=proposal[2],
                    proposer_reasoning=proposal[10],
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
        """Execute any proposals that have passed voting but not yet been executed."""
        count = self.execution.get_proposal_count()
        new_markets = []

        for proposal_id in range(count):
            try:
                proposal = self.execution.governance.functions.proposals(proposal_id).call()
                executed = proposal[8]
                voting_deadline = proposal[7]
                votes_for = proposal[5]
                votes_against = proposal[6]

                if executed:
                    continue
                if int(time.time()) <= voting_deadline:
                    continue
                if votes_for <= votes_against:
                    continue

                result = self.execution.execute_proposal(proposal_id)
                market_addr = result["receipt"]["logs"][0]["address"] if result["receipt"].get("logs") else ""
                self.log(f"[{self.agent_id}] Executed proposal #{proposal_id} → market {market_addr}")
                new_markets.append(market_addr)
            except Exception as e:
                self.log(f"[{self.agent_id}] Execute error on #{proposal_id}: {e}")

        return new_markets
