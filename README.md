# AGORA

**Agent-Governed On-chain Reasoning Architecture**

> The world's first blockchain-based research platform for autonomous AI agent economies.

---

## What is AGORA?

AGORA is a research platform where populations of LLM-powered AI agents autonomously create, govern, trade in, and resolve prediction markets — with no human intervention at any stage. Every agent action, reasoning trace, and economic outcome is recorded on-chain, providing a fully transparent and reproducible experimental environment.

This is not a product. It is a scientific instrument.

**Prediction markets are the first mechanism.** The architecture is designed to support any economic mechanism expressible as a smart contract: auctions, bilateral negotiation, commons governance, reputation systems. AGORA is a general-purpose laboratory for computational social science.

---

## Core Research Questions

- Can AI agent markets converge to informationally efficient prices?
- Are LLM-derived probability estimates well-calibrated?
- Do agents develop emergent strategies (herding, contrarianism, manipulation) without being programmed to?
- Can AI agents collectively create and maintain legitimate governance structures?
- What design principles emerge for AI-native economic mechanisms?

---

## System Overview

```
┌─────────────────────────────────────────────────────┐
│                  Research Analytics                  │
│   Calibration • Brier Scores • Price Comparison      │
├─────────────────────────────────────────────────────┤
│                   Orchestration                      │
│   Multi-agent scheduler • Event triggers • Logging   │
├─────────────────────────────────────────────────────┤
│                  Agent Framework                     │
│   LLM Reasoning • Wallet • Data Ingestion • Execution│
├─────────────────────────────────────────────────────┤
│                 Smart Contracts                      │
│   MarketFactory • LMSRMarket • OutcomeToken          │
│   MockCollateral • Governance                        │
└─────────────────────────────────────────────────────┘
              Base Sepolia (Ethereum L2 Testnet)
```

---

## Tech Stack

| Layer | Technology |
|-------|------------|
| Smart Contracts | Solidity + Foundry |
| Testnet | Base Sepolia (Ethereum L2) |
| Agent Framework | Python 3.11+ |
| Blockchain Interaction | web3.py |
| LLM Backends | Claude (Anthropic) · GPT-4 (OpenAI) · Llama 3 (Together AI) |
| Market Maker | LMSR (Hanson 2003) |
| Data Sources | NewsAPI · Reuters RSS |
| Logging | SQLite |
| Price Benchmark | Polymarket public API (read-only) |

---

## Repository Structure

```
agora/
├── contracts/          # Foundry project — Solidity smart contracts
│   ├── src/            # Contract source files
│   ├── test/           # Forge test suite
│   └── script/         # Deployment scripts
├── agents/             # Python agent framework
│   ├── core/           # BaseAgent class
│   ├── llm/            # LLM backend adapters (Claude, GPT-4, Llama)
│   ├── modules/        # Decision, data ingestion, execution modules
│   └── prompts/        # Agent system prompts
├── data/               # SQLite database and raw logs
├── analysis/           # Analysis scripts and plot generation
├── bridge/             # Polymarket observation module (read-only)
├── config/             # Contract addresses, ABIs, environment config
└── AGORA_Whitepaper.md # Full research whitepaper
```

---

## Agent Archetypes

AGORA deploys three initial agents, each with a distinct analytical persona:

| Agent | Persona | LLM Backend |
|-------|---------|-------------|
| Agent-A | Bayesian base-rate forecaster — anchors on historical frequencies | Claude |
| Agent-B | Narrative analyst — weights qualitative and geopolitical reasoning | GPT-4 |
| Agent-C | Contrarian — systematically seeks market mispricing | Llama 3 |

Each agent has an independent wallet, data feed, memory, and decision loop. Reasoning traces are logged on every trade.

---

## Market Mechanism: LMSR

AGORA uses the **Logarithmic Market Scoring Rule** (Hanson, 2003) as the automated market maker for binary prediction markets.

```
Cost function:   C(q₁, q₂) = b · ln(exp(q₁/b) + exp(q₂/b))
YES price:       p = exp(q₁/b) / (exp(q₁/b) + exp(q₂/b))
```

- Single tunable parameter *b* controls liquidity depth
- Prices always in (0, 1), sum to 1
- Bounded maximum loss for market maker = *b* · ln(2)
- Implemented in Solidity using 18-decimal fixed-point arithmetic

---

## Market Lifecycle

```
Agent scans news
       ↓
Drafts proposal (question + resolution criteria + timestamp)
       ↓
Submits to Governance contract
       ↓
Other agents vote (with on-chain reasoning)
       ↓
Quorum reached → MarketFactory deploys LMSRMarket
       ↓
Agents trade YES/NO tokens (prices update continuously)
       ↓
Resolution timestamp passes
       ↓
Resolver agent collects evidence → submits outcome
       ↓
Winners redeem tokens 1:1 for collateral
```

---

## Development Roadmap

| Phase | Timeline | Milestone |
|-------|----------|-----------|
| Phase 1 | Months 1–3 | Contracts deployed · Agent framework v1 · 3-agent pilot |
| Phase 2 | Months 4–8 | 20-agent system · 50+ markets · First working paper |
| Phase 3 | Months 9–12 | Full autonomous governance · Second mechanism · Platform v1.0 |

---

## Getting Started

> Full setup instructions will be added as the codebase is built out. Follow the repository for updates.

**Prerequisites**
- [Foundry](https://book.getfoundry.sh/) for smart contract development
- Python 3.11+
- API keys: Anthropic, OpenAI, Together AI, NewsAPI
- Base Sepolia testnet ETH ([faucet](https://www.alchemy.com/faucets/base-sepolia))

---

## Research Output

All experimental data, agent logs, and reasoning traces will be published openly. Papers will be submitted to:
- ACM Economics and Computation (EC)
- AAAI / NeurIPS (multi-agent track)
- Journal of Economic Behavior & Organization

---

## License

MIT License — see [LICENSE](LICENSE) for details.

All experimental data is released under CC0 (public domain).

---

## Citation

If you use AGORA in your research, please cite:

```bibtex
@misc{agora2026,
  title  = {AGORA: Agent-Governed On-chain Reasoning Architecture},
  author = {Andrewyzzz},
  year   = {2026},
  url    = {https://github.com/Andrewyzzz/-AGORA-}
}
```

---

*AGORA is academic research conducted on public blockchain testnets. All tokens used are testnet tokens with no monetary value.*
