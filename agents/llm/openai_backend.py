"""
GPT-4 (OpenAI) LLM backend.
"""
import json
import os
from typing import Optional
from openai import OpenAI
from .base import LLMBackend, TradeDecision, ProposalDecision, VoteDecision, ResolutionDecision


class OpenAIBackend(LLMBackend):
    def __init__(self, system_prompt: str, model: str = "gpt-4o"):
        super().__init__(model_name=model, system_prompt=system_prompt)
        self.client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])

    def _call(self, user_message: str, model_class) -> dict:
        response = self.client.beta.chat.completions.parse(
            model=self.model_name,
            messages=[
                {"role": "system", "content": self.system_prompt},
                {"role": "user", "content": user_message},
            ],
            response_format=model_class,
        )
        return json.loads(response.choices[0].message.content)

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
        result = self._call(prompt, TradeDecision)
        return TradeDecision(**result)

    def get_proposal_decision(self, recent_news, existing_markets) -> Optional[ProposalDecision]:
        news_str = "\n".join(f"- {n}" for n in recent_news[:15])
        markets_str = "\n".join(f"- {m}" for m in existing_markets[:10]) or "None yet."
        prompt = f"""RECENT NEWS:
{news_str}

EXISTING MARKETS (avoid duplicating):
{markets_str}

Identify ONE upcoming event that would make a valuable prediction market.
If nothing compelling exists, set question to empty string."""
        result = self._call(prompt, ProposalDecision)
        if not result.get("question"):
            return None
        return ProposalDecision(**result)

    def get_vote_decision(self, question, resolution_criteria, proposer_reasoning) -> VoteDecision:
        prompt = f"""PROPOSED MARKET:
Question: {question}
Resolution Criteria: {resolution_criteria}
Proposer's Reasoning: {proposer_reasoning}

Should this market be created? Vote FOR or AGAINST."""
        result = self._call(prompt, VoteDecision)
        return VoteDecision(**result)

    def get_resolution_decision(self, question, resolution_criteria,
                                evidence_sources) -> ResolutionDecision:
        sources_str = "\n".join(f"- {s}" for s in evidence_sources)
        prompt = f"""MARKET TO RESOLVE:
Question: {question}
Resolution Criteria: {resolution_criteria}

EVIDENCE SOURCES:
{sources_str}

Determine the resolution outcome (YES or NO)."""
        result = self._call(prompt, ResolutionDecision)
        return ResolutionDecision(**result)
