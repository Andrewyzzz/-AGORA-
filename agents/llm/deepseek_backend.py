"""
DeepSeek LLM backend.
Uses OpenAI-compatible API with DeepSeek's base URL.
"""
import json
import os
from typing import Optional
from openai import OpenAI
from .base import LLMBackend, TradeDecision, ProposalDecision, VoteDecision, ResolutionDecision

_DEEPSEEK_BASE_URL = "https://api.deepseek.com"
_DEFAULT_MODEL = "deepseek-chat"


class DeepSeekBackend(LLMBackend):
    def __init__(self, system_prompt: str, model: str = _DEFAULT_MODEL):
        super().__init__(model_name=model, system_prompt=system_prompt)
        self.client = OpenAI(
            api_key=os.environ["DEEPSEEK_API_KEY"],
            base_url=_DEEPSEEK_BASE_URL,
        )

    def _call(self, user_message: str, schema: dict) -> dict:
        schema_str = json.dumps(schema, indent=2)
        system = (
            f"{self.system_prompt}\n\n"
            f"You MUST respond with ONLY valid JSON matching this schema:\n{schema_str}"
        )
        response = self.client.chat.completions.create(
            model=self.model_name,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user_message},
            ],
            response_format={"type": "json_object"},
            max_tokens=1024,
            temperature=0.3,
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

Provide your trading decision."""
        result = self._call(prompt, TradeDecision.model_json_schema())
        return TradeDecision(**result)

    def get_proposal_decision(self, recent_news, existing_markets) -> Optional[ProposalDecision]:
        news_str = "\n".join(f"- {n}" for n in recent_news[:15])
        markets_str = "\n".join(f"- {m}" for m in existing_markets[:10]) or "None yet."
        prompt = f"""RECENT NEWS:
{news_str}

EXISTING MARKETS (avoid duplicating):
{markets_str}

Propose ONE new prediction market. Set question to empty string if none."""
        result = self._call(prompt, ProposalDecision.model_json_schema())
        if not result.get("question"):
            return None
        return ProposalDecision(**result)

    def get_vote_decision(self, question, resolution_criteria, proposer_reasoning) -> VoteDecision:
        prompt = f"""PROPOSED MARKET:
Question: {question}
Resolution Criteria: {resolution_criteria}
Proposer's Reasoning: {proposer_reasoning}

Vote FOR or AGAINST."""
        result = self._call(prompt, VoteDecision.model_json_schema())
        return VoteDecision(**result)

    def get_resolution_decision(self, question, resolution_criteria,
                                evidence_sources) -> ResolutionDecision:
        sources_str = "\n".join(f"- {s}" for s in evidence_sources)
        prompt = f"""MARKET TO RESOLVE:
Question: {question}
Resolution Criteria: {resolution_criteria}
Evidence: {sources_str}

Determine the resolution outcome (YES or NO)."""
        result = self._call(prompt, ResolutionDecision.model_json_schema())
        return ResolutionDecision(**result)
