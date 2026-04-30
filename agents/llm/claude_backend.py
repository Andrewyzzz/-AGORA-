"""
Claude (Anthropic) LLM backend.
"""
import json
import os
from typing import Optional
import anthropic
from .base import LLMBackend, TradeDecision, ProposalDecision, VoteDecision, ResolutionDecision

TRADE_SCHEMA = TradeDecision.model_json_schema()
PROPOSAL_SCHEMA = ProposalDecision.model_json_schema()
VOTE_SCHEMA = VoteDecision.model_json_schema()
RESOLUTION_SCHEMA = ResolutionDecision.model_json_schema()


class ClaudeBackend(LLMBackend):
    def __init__(self, system_prompt: str, model: str = os.environ.get("CLAUDE_MODEL", "claude-opus-4-6")):
        super().__init__(model_name=model, system_prompt=system_prompt)
        self.client = anthropic.Anthropic(
            api_key=os.environ["ANTHROPIC_API_KEY"],
            base_url=os.environ.get("ANTHROPIC_BASE_URL", "https://api.anthropic.com"),
        )

    def _call(self, user_message: str, schema: dict) -> dict:
        response = self.client.messages.create(
            model=self.model_name,
            max_tokens=1024,
            system=self.system_prompt,
            messages=[{"role": "user", "content": user_message}],
            tools=[{
                "name": "structured_output",
                "description": "Return your decision as structured JSON",
                "input_schema": schema,
            }],
            tool_choice={"type": "tool", "name": "structured_output"},
        )
        for block in response.content:
            if block.type == "tool_use":
                return block.input
        raise ValueError("Claude did not return tool use block")

    def get_trade_decision(self, question, resolution_criteria, current_yes_price,
                           recent_news, memory) -> TradeDecision:
        news_str = "\n".join(f"- {n}" for n in recent_news[:10])
        memory_str = "\n".join(f"- {m}" for m in memory[-5:]) if memory else "None yet."
        prompt = f"""PREDICTION MARKET QUESTION:
{question}

RESOLUTION CRITERIA:
{resolution_criteria}

CURRENT MARKET PRICE (YES): {current_yes_price:.1%}

RECENT NEWS:
{news_str}

YOUR RECENT MEMORY:
{memory_str}

Based on your analytical approach and the above information, provide your trading decision."""
        result = self._call(prompt, TRADE_SCHEMA)
        return TradeDecision(**result)

    def get_proposal_decision(self, recent_news, existing_markets) -> Optional[ProposalDecision]:
        news_str = "\n".join(f"- {n}" for n in recent_news[:15])
        markets_str = "\n".join(f"- {m}" for m in existing_markets[:10]) or "None yet."
        prompt = f"""RECENT NEWS:
{news_str}

EXISTING MARKETS (avoid duplicating):
{markets_str}

Identify ONE upcoming FUTURE event that would make a valuable prediction market.
IMPORTANT RULES:
- The event MUST be in the future (has not happened yet)
- The question must be answerable YES or NO after the resolution date
- Do NOT propose markets about events that have already occurred
- If the first item in the news says today's date, use that to judge what is future vs past
- If nothing compelling exists, set question to empty string."""
        result = self._call(prompt, PROPOSAL_SCHEMA)
        if not result.get("question"):
            return None
        return ProposalDecision(**result)

    def get_vote_decision(self, question, resolution_criteria, proposer_reasoning) -> VoteDecision:
        prompt = f"""PROPOSED MARKET:
Question: {question}
Resolution Criteria: {resolution_criteria}
Proposer's Reasoning: {proposer_reasoning}

Should this market be created? Vote FOR or AGAINST with your reasoning."""
        result = self._call(prompt, VOTE_SCHEMA)
        return VoteDecision(**result)

    def get_resolution_decision(self, question, resolution_criteria,
                                evidence_sources) -> ResolutionDecision:
        sources_str = "\n".join(f"- {s}" for s in evidence_sources)
        prompt = f"""MARKET TO RESOLVE:
Question: {question}
Resolution Criteria: {resolution_criteria}

EVIDENCE SOURCES TO CHECK:
{sources_str}

Based on available evidence, determine the resolution outcome (YES or NO)."""
        result = self._call(prompt, RESOLUTION_SCHEMA)
        return ResolutionDecision(**result)
