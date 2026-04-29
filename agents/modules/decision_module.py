"""
Decision module — wraps the LLM backend to produce trade and governance actions.
Handles retries, structured output validation, and memory injection.
"""
import time
from agents.llm.base import LLMBackend, TradeDecision, ProposalDecision, VoteDecision, ResolutionDecision


ACTION_TO_OUTCOME = {
    "BUY_YES": (0, "buy"),
    "BUY_NO": (1, "buy"),
    "SELL_YES": (0, "sell"),
    "SELL_NO": (1, "sell"),
    "HOLD": (None, "hold"),
}


class DecisionModule:
    def __init__(self, llm: LLMBackend, max_retries: int = 3):
        self.llm = llm
        self.max_retries = max_retries

    def decide_trade(
        self,
        question: str,
        resolution_criteria: str,
        current_yes_price: float,
        recent_news: list[str],
        memory: list[str],
    ) -> TradeDecision:
        for attempt in range(self.max_retries):
            try:
                return self.llm.get_trade_decision(
                    question, resolution_criteria,
                    current_yes_price, recent_news, memory,
                )
            except Exception as e:
                if attempt == self.max_retries - 1:
                    raise
                time.sleep(2 ** attempt)

    def decide_proposal(
        self,
        recent_news: list[str],
        existing_markets: list[str],
    ) -> ProposalDecision | None:
        for attempt in range(self.max_retries):
            try:
                return self.llm.get_proposal_decision(recent_news, existing_markets)
            except Exception as e:
                if attempt == self.max_retries - 1:
                    return None
                time.sleep(2 ** attempt)

    def decide_vote(
        self,
        question: str,
        resolution_criteria: str,
        proposer_reasoning: str,
    ) -> VoteDecision:
        for attempt in range(self.max_retries):
            try:
                return self.llm.get_vote_decision(question, resolution_criteria, proposer_reasoning)
            except Exception as e:
                if attempt == self.max_retries - 1:
                    raise
                time.sleep(2 ** attempt)

    def decide_resolution(
        self,
        question: str,
        resolution_criteria: str,
        evidence_sources: list[str],
    ) -> ResolutionDecision:
        for attempt in range(self.max_retries):
            try:
                return self.llm.get_resolution_decision(question, resolution_criteria, evidence_sources)
            except Exception as e:
                if attempt == self.max_retries - 1:
                    raise
                time.sleep(2 ** attempt)

    @staticmethod
    def parse_action(decision: TradeDecision) -> tuple[int | None, str, float]:
        """Returns (outcome_int_or_None, 'buy'/'sell'/'hold', amount_tokens)."""
        outcome, action_type = ACTION_TO_OUTCOME.get(decision.action, (None, "hold"))
        return outcome, action_type, decision.amount_tokens
