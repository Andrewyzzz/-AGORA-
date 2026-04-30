"""
Abstract base class and shared data models for all LLM backends.
"""
from abc import ABC, abstractmethod
from typing import Optional
from pydantic import BaseModel, Field


class TradeDecision(BaseModel):
    """Structured output from the trading decision module."""
    probability_estimate: float = Field(ge=0.0, le=1.0,
        description="Estimated probability of YES outcome (0-1)")
    confidence: str = Field(pattern="^(low|medium|high)$",
        description="Confidence level in the estimate")
    key_factors: list[str] = Field(max_length=8,
        description="Top factors driving this estimate")
    reasoning: str = Field(
        description="Full chain-of-thought reasoning")
    action: str = Field(pattern="^(BUY_YES|BUY_NO|SELL_YES|SELL_NO|HOLD)$",
        description="Trading action to take")
    amount_tokens: float = Field(ge=0.0,
        description="Number of tokens to trade (in WAD units, e.g. 5.0 = 5 tokens)")
    rationale: str = Field(
        description="Brief rationale for this specific trade")


class ProposalDecision(BaseModel):
    """Structured output when an agent proposes a new market."""
    question: str = Field(description="The binary prediction question")
    resolution_criteria: str = Field(
        description="Precise, unambiguous criteria for YES resolution, including data sources and edge cases")
    resolution_days: int = Field(ge=1, le=365,
        description="Days from now until resolution")
    liquidity_parameter: int = Field(ge=50, le=1000,
        description="LMSR liquidity parameter b (higher = deeper market)")
    reasoning: str = Field(description="Why this is a valuable prediction market")


class VoteDecision(BaseModel):
    """Structured output when an agent votes on a governance proposal."""
    support: bool = Field(description="True = vote FOR, False = vote AGAINST")
    reasoning: str = Field(description="Justification for this vote")


class ResolutionDecision(BaseModel):
    """Structured output when an agent resolves a market."""
    outcome: str = Field(pattern="^(YES|NO)$",
        description="Market resolution outcome")
    confidence: str = Field(pattern="^(low|medium|high)$")
    evidence: list[str] = Field(description="Evidence supporting this resolution")
    reasoning: str = Field(description="Full reasoning for this resolution")


class LLMBackend(ABC):
    """Abstract base for all LLM backends (Claude, GPT-4, Llama)."""

    def __init__(self, model_name: str, system_prompt: str):
        self.model_name = model_name
        self.system_prompt = system_prompt

    @abstractmethod
    def get_trade_decision(
        self,
        question: str,
        resolution_criteria: str,
        current_yes_price: float,
        recent_news: list[str],
        memory: list[str],
    ) -> TradeDecision:
        """Return a structured trading decision for a given market."""

    @abstractmethod
    def get_proposal_decision(
        self,
        recent_news: list[str],
        existing_markets: list[str],
    ) -> Optional[ProposalDecision]:
        """Return a new market proposal, or None if no good opportunity found."""

    @abstractmethod
    def get_vote_decision(
        self,
        question: str,
        resolution_criteria: str,
        proposer_reasoning: str,
    ) -> VoteDecision:
        """Return a vote on a governance proposal."""

    @abstractmethod
    def get_resolution_decision(
        self,
        question: str,
        resolution_criteria: str,
        evidence_sources: list[str],
    ) -> ResolutionDecision:
        """Return a resolution decision for an expired market."""
