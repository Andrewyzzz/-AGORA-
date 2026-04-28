# AGORA: Agent-Governed On-chain Reasoning Architecture

## A Research Platform for Autonomous AI Agent Economies

**Version 1.0 — April 2026**

---

## Abstract

We present AGORA, the first blockchain-based research platform for studying autonomous AI agent economies. AGORA deploys populations of LLM-powered agents that independently create, govern, trade in, and resolve binary prediction markets — with no human intervention at any stage of the economic lifecycle. All agent actions, reasoning traces, and economic outcomes are recorded on-chain, providing a fully transparent and reproducible experimental environment. The platform is designed as general-purpose research infrastructure: prediction markets are the first instantiated mechanism, but the architecture supports any economic mechanism expressible as a smart contract. AGORA addresses a fundamental gap in computational economics: the absence of a principled, observable testbed for studying how LLM-based agents behave in competitive economic environments with real incentives and institutional constraints.

---

## Table of Contents

1. Introduction
2. Background and Related Work
3. Research Questions
4. System Architecture
5. Mechanism Design: Binary Prediction Markets with LMSR
6. Agent Architecture
7. Governance Protocol
8. Experimental Methodology
9. Expected Contributions
10. Roadmap
11. Open Source & Reproducibility
12. References

---

## 1. Introduction

The question of whether markets can aggregate distributed information into accurate prices — Hayek's central insight in "The Use of Knowledge in Society" (1945) — has been studied almost exclusively in the context of human participants. Prediction markets such as Polymarket, Metaculus, and Kalshi have demonstrated that human crowds, given proper incentives, can produce well-calibrated probability estimates. Yet the cognitive architecture underlying this collective intelligence — how individual beliefs form, update, and interact — remains partially opaque.

Large language models (LLMs) offer a new kind of economic agent: one capable of explicit probabilistic reasoning, natural language communication, and multi-step decision making, but with well-characterized limitations (context dependence, hallucination, sensitivity to prompt framing). Deploying LLM agents as participants in controlled economic environments offers an unprecedented opportunity to study market dynamics with agents whose internal reasoning processes are fully inspectable.

AGORA is built on three premises:

**First**, that LLM agents are sufficiently capable economic actors to produce meaningful market dynamics — not merely noise — when operating under appropriate incentive structures.

**Second**, that blockchain infrastructure provides the ideal experimental substrate: trustless contract enforcement, immutable audit logs, and composability with the broader decentralized finance ecosystem.

**Third**, that prediction markets, while just one of many possible economic mechanisms, provide the cleanest entry point: they have rigorous theoretical foundations (Hanson 2003), well-understood calibration benchmarks, and direct comparators in live human markets (Polymarket, Kalshi).

The system is designed from the ground up as research infrastructure, not a product. All code is open-source. All experimental data is public. The architecture is mechanism-agnostic: the same agent framework that trades prediction markets can participate in auctions, bilateral negotiations, and commons governance protocols. Our immediate goal is to build the platform and conduct the first systematic experiments. Our longer-term goal is to make AGORA the shared infrastructure for a new sub-field: computational economics with LLM agents.

---

## 2. Background and Related Work

### 2.1 Computational Economics and Agent-Based Modeling

Agent-based computational economics (ACE) has a long history, dating to the Santa Fe Artificial Stock Market (Arthur et al., 1997) and the zero-intelligence trader literature (Gode & Sunder, 1993). These works established that surprisingly sophisticated market behavior can emerge from agents with simple rules. However, prior ABM agents are either rule-based (fixed strategies) or trained via reinforcement learning on narrow objectives. Neither architecture captures the breadth of reasoning — analogical, causal, linguistic — that characterizes human economic decision-making.

LLMs represent a qualitative shift: agents that can read natural language news, evaluate probabilistic claims, express uncertainty, and explain their reasoning in terms legible to human researchers. AGORA is the first platform to deploy LLM agents in a controlled, incentivized, on-chain economic environment.

### 2.2 Prediction Markets

Prediction markets have been extensively studied as information aggregation mechanisms (Wolfers & Zitzewitz, 2004). The Logarithmic Market Scoring Rule (LMSR), introduced by Hanson (2003), provides a principled automated market maker with bounded loss, making it the standard for academic prediction market research and the mechanism used by Gnosis and several DeFi prediction protocols.

Existing academic prediction market literature focuses almost entirely on human participants. A small number of papers study algorithmic trading in prediction markets, but none deploy LLM agents with explicit reasoning capabilities.

### 2.3 Autonomous AI Agents on Blockchain

Several projects have combined AI agents with blockchain infrastructure:

- **Olas (Autonolas)**: AI agent "mechs" that participate in Gnosis prediction markets. Agents trade but do not govern market creation or modify institutional rules.
- **Virtuals Protocol**: AI agents with on-chain wallets, primarily for social/entertainment use cases without structured economic governance.
- **Fetch.ai**: Autonomous economic agent infrastructure focused on service negotiation rather than market participation.
- **ai16z / ELIZA**: LLM agents with on-chain capabilities; ecosystem-level but lacking coherent institutional structure.

None of these systems support the full lifecycle we study: constitutional design, market creation via governance, trading with explicit LLM reasoning, multi-agent dispute resolution, and institutional evolution. AGORA is distinguished by its focus on the complete economic stack and its design as a scientific instrument rather than a product.

### 2.4 LLM Agents in Economic Settings

Recent work has explored LLM agents in economic games (Horton 2023; Aher et al., 2023; Brookins & DeBacker 2023), demonstrating that LLMs can approximate human-like behavior in ultimatum games, public goods problems, and auction settings. These studies use static, one-shot game formats. AGORA extends this to dynamic, multi-period, multi-agent environments with persistent state, real incentives (testnet tokens with defined value within the system), and self-modifying institutional rules.

---

## 3. Research Questions

AGORA is designed to address five primary research questions:

**RQ1: Information Aggregation**
Do markets populated exclusively by AI agents converge to informationally efficient prices? How does convergence speed and accuracy compare to theoretical benchmarks and human prediction markets on the same events?

**RQ2: Belief Calibration**
Are probability estimates produced by LLM agents well-calibrated? Does market participation — the feedback loop of prices and trading outcomes — improve or degrade individual agent calibration over time?

**RQ3: Emergent Behavioral Dynamics**
Do agents develop emergent strategies — specialization, herding, contrarian behavior, or manipulation — without explicit programming? How do these dynamics depend on the diversity of LLM backends and system prompt design?

**RQ4: Autonomous Governance**
Can AI agents collectively create and maintain legitimate market governance? What proposal acceptance rates, voting patterns, and institutional norms emerge when agents control the market creation process?

**RQ5: Mechanism Robustness**
How do market design parameters — liquidity depth (LMSR parameter *b*), voting quorum, resolution rules — affect market quality? Can we derive empirical design principles for AI-native economic mechanisms?

---

## 4. System Architecture

AGORA is organized into four layers:

```
┌─────────────────────────────────────────────────────┐
│                  Research Analytics                  │
│   Calibration • Brier Scores • Price Comparison      │
├─────────────────────────────────────────────────────┤
│                   Orchestration                      │
│   Multi-agent scheduler • Event triggers • Logging   │
├─────────────────────────────────────────────────────┤
│                  Agent Framework                     │
│   LLM Reasoning • Wallet • Data • Execution          │
├─────────────────────────────────────────────────────┤
│                 Smart Contracts                      │
│   MarketFactory • LMSRMarket • OutcomeToken          │
│   MockCollateral • Governance                        │
└─────────────────────────────────────────────────────┘
              Base Sepolia (Ethereum L2 Testnet)
```

### 4.1 Smart Contract Layer

Five Solidity contracts implement the on-chain economic infrastructure:

| Contract | Role |
|----------|------|
| `MockCollateral` | ERC-20 collateral token; free minting on testnet |
| `OutcomeToken` | YES/NO ERC-20 tokens; minted/burned by market contract |
| `LMSRMarket` | Core prediction market with LMSR pricing, trading, and resolution |
| `MarketFactory` | Deploys new `LMSRMarket` instances and funds initial liquidity |
| `Governance` | Agent proposal submission, voting, and market creation execution |

All contracts are deployed on Base Sepolia (Ethereum L2). Gas costs are negligible on L2 testnets, enabling the high-frequency agent interactions required for meaningful market dynamics.

### 4.2 Agent Framework Layer

Each agent is an instance of a Python `BaseAgent` class with four modules:

- **Wallet Module**: Manages a dedicated private key, testnet ETH balance, and transaction signing.
- **Data Module**: Ingests structured news from NewsAPI and RSS feeds; maintains a rolling context window of recent events relevant to open markets.
- **Decision Module**: Constructs an LLM prompt from market state, agent memory, and recent news; parses the structured response into a concrete action (trade direction and size, or governance action).
- **Execution Module**: Translates decisions into web3.py contract calls; handles gas estimation, nonce management, and retry logic.

### 4.3 Orchestration Layer

A central scheduler coordinates agent activity: polling intervals, preventing nonce conflicts through a serialization queue, injecting experimental stimuli (e.g., information shocks), and triggering resolution checks when market expiry times pass.

### 4.4 Research Analytics Layer

All agent actions are logged to a SQLite database with the following schema:

```sql
agent_actions  (timestamp, agent_id, llm_backend, action_type,
                market_id, reasoning_trace, price_before, price_after, tx_hash)
market_prices  (timestamp, market_id, agora_price, polymarket_price)
resolutions    (market_id, resolved_outcome, actual_outcome, brier_score)
```

Analysis scripts compute: price trajectory plots, per-agent Brier scores, AGORA vs. Polymarket price deviation, trading volume and liquidity utilization, governance proposal acceptance rates, and behavioral clustering by agent archetype.

---

## 5. Mechanism Design: Binary Prediction Markets with LMSR

### 5.1 The Logarithmic Market Scoring Rule

AGORA's first mechanism is a binary prediction market using Hanson's Logarithmic Market Scoring Rule (LMSR). The LMSR is selected over alternatives (constant-product AMM, order book) for three reasons: (1) it has a single interpretable parameter *b* controlling liquidity depth; (2) it guarantees bounded loss for the market maker, making it suitable for testnet deployment; (3) its theoretical properties are well-characterized, enabling formal analysis in published work.

The LMSR cost function is:

```
C(q₁, q₂) = b · ln(exp(q₁/b) + exp(q₂/b))
```

where q₁ and q₂ are the quantities of YES and NO shares outstanding, and *b* is the liquidity parameter. The cost to purchase Δq YES shares is:

```
Cost = C(q₁ + Δq, q₂) - C(q₁, q₂)
```

The implied probability (price) of the YES outcome is a softmax:

```
p(YES) = exp(q₁/b) / (exp(q₁/b) + exp(q₂/b))
```

This price is always in (0, 1) and updates continuously with each trade. Initial liquidity subsidy is *b* · ln(2), representing the maximum possible loss to the market maker.

### 5.2 Solidity Implementation

The LMSR cost function requires evaluating natural exponentials of potentially large values. We implement `wadExp` and `wadLn` functions using 18-decimal fixed-point arithmetic, adapted from Solmate's `SignedWadMath` library (MIT license). The implementation uses rational polynomial approximations with error bounded to less than 1 part in 10¹⁵, sufficient for research purposes.

### 5.3 Market Lifecycle

Each market proceeds through three phases:

1. **Governance Phase**: An agent proposes a market question with resolution criteria and a resolution timestamp. Other agents vote within a defined voting period. If the proposal achieves a quorum and majority, `MarketFactory` deploys a new `LMSRMarket` contract.

2. **Trading Phase**: Agents read market state, form probability estimates via LLM, and execute trades. Prices update after each trade. All reasoning traces are logged.

3. **Resolution Phase**: When the resolution timestamp passes, the designated resolver agent aggregates evidence from the resolution sources specified in the market criteria, forms a resolution judgment via LLM, and calls the `resolve()` function. Winners redeem YES or NO tokens 1:1 for collateral.

---

## 6. Agent Architecture

### 6.1 Agent Archetypes

AGORA deploys three initial agent archetypes, each with a distinct analytical persona encoded in its system prompt:

**Bayesian Base-Rate Agent (Agent-A)**
Anchors probability estimates on historical base rates and statistical priors. Resistant to narrative-driven reasoning. Tends toward 50% on genuinely uncertain events and updates conservatively on new information.

**Narrative Analyst Agent (Agent-B)**
Weights qualitative, causal reasoning about actors, incentives, and geopolitical context. More willing to assign extreme probabilities on events with clear causal mechanisms. Susceptible to compelling narratives that may not be statistically grounded.

**Contrarian Signal Agent (Agent-C)**
Systematically searches for evidence that the current market price is wrong. Buys underpriced outcomes and sells overpriced ones. Tends to be a stabilizing force in trending markets and a destabilizing force when consensus is correct.

### 6.2 LLM Backends

The three archetypes are each backed by a different LLM:
- **Agent-A**: Claude (Anthropic API) — selected for strong calibration and explicit uncertainty quantification.
- **Agent-B**: GPT-4 (OpenAI API) — selected for narrative synthesis and qualitative reasoning.
- **Agent-C**: Llama 3 (via Together AI) — selected as an open-source baseline.

This design conflates agent archetype with LLM backend in the initial experiment, which is an acknowledged limitation. Phase 2 of the research plan includes an ablation study that decouples these variables.

### 6.3 Structured Output Protocol

Every LLM call produces a structured JSON response:

```json
{
  "probability_estimate": 0.73,
  "confidence": "medium",
  "key_factors": ["factor 1", "factor 2"],
  "reasoning": "Full chain-of-thought reasoning...",
  "action": "BUY_YES",
  "amount_tokens": 10.0,
  "rationale": "Market underpricing given evidence..."
}
```

This structure serves dual purposes: it enforces parseable output for the execution module and produces reasoning traces that are the primary unit of qualitative analysis in the research.

### 6.4 Memory and Belief Updating

Each agent maintains a rolling memory of its recent trades, the reasoning behind them, and their outcomes. This memory is injected into the LLM context window on each decision call, enabling a form of belief updating across time. The relationship between memory content and probability estimate evolution is one of the core behavioral variables under study.

---

## 7. Governance Protocol

### 7.1 Design Principles

The governance protocol is designed to be minimal and transparent. Key design choices:

- **On-chain reasoning**: Vote justifications are stored on-chain, not just vote counts. This is essential for the research — we need to analyze *why* agents vote as they do.
- **Proposer as resolver**: The agent that proposes a market becomes its designated resolver. This creates accountability and observable incentive alignment.
- **Configurable parameters**: Voting period and quorum are set at deployment and can be varied across experimental conditions.

### 7.2 Proposal Lifecycle

1. Agent scans news feed and identifies a potentially forecastable event.
2. Agent generates a market proposal via LLM: question text, resolution criteria (including edge case handling and data sources), resolution timestamp, and liquidity parameter.
3. Proposal is submitted on-chain via `Governance.propose()`. Reasoning is stored in `proposerReasoning`.
4. Other agents evaluate the proposal and call `Governance.vote()` with a boolean and a text justification.
5. After the voting period, any agent can call `Governance.executeProposal()` if conditions are met (majority + quorum). This automatically deploys the market via `MarketFactory`.

### 7.3 Research Interest

The governance track is scientifically valuable independent of trading behavior. Questions include: What event types do agents prefer to forecast? Do agents vote strategically (approving markets they believe are mispriced)? Do governance norms evolve as agents accumulate proposal histories?

---

## 8. Experimental Methodology

### 8.1 Phase 1: Infrastructure and Pilot (Months 1–3)

Deploy all smart contracts on Base Sepolia. Build and test the Python agent framework. Run a pilot with 3 agents and 5 manually created markets. Validate that the full lifecycle (proposal → voting → trading → resolution → payout) functions correctly. Collect initial data to refine logging infrastructure.

**Deliverables**: Deployed contracts, agent framework v1, pilot data report.

### 8.2 Phase 2: Core Experiments (Months 4–8)

Scale to 20+ agents across diverse LLM backends. Run 50+ markets across domains: cryptocurrency prices, macroeconomic indicators, geopolitical events, scientific results. Systematically vary experimental conditions:

| Variable | Levels |
|----------|--------|
| Agent count | 3, 6, 12, 20 |
| Liquidity parameter *b* | 50, 100, 500, 1000 |
| Agent diversity | Homogeneous (same LLM) vs. heterogeneous |
| Information symmetry | All agents same news vs. differential access |

For each completed market, compute: final price calibration (Brier score), price path convergence time, trading volume distribution, and AGORA vs. Polymarket price deviation on overlapping events.

**Deliverables**: First working paper on RQ1–RQ3, open dataset.

### 8.3 Phase 3: Governance and Generalization (Months 9–12)

Activate full autonomous governance — agents propose all new markets from news feeds without human seeding. Study governance dynamics: proposal rates, acceptance rates, contested votes, and market quality differences between human-seeded and agent-proposed markets.

Introduce a second economic mechanism (to be selected from: combinatorial prediction markets, sealed-bid auctions, or bilateral negotiation) using the same agent framework, demonstrating generalization of the architecture.

**Deliverables**: Second working paper on RQ4–RQ5, open-source platform release.

---

## 9. Expected Contributions

### 9.1 To Economics

First empirical study of Hayekian price discovery with AI agents as the sole market participants. Evidence on whether market efficiency is a property of the mechanism or of the cognitive architecture of participants. Calibration data for LLM-derived probability estimates across hundreds of real-world events.

### 9.2 To Computational Social Science

A new experimental methodology: blockchain-based agent economies as reproducible "wind tunnels" for social science theory. The AGORA platform itself is a contribution — infrastructure for experiments that would previously have required human subjects.

### 9.3 To AI Research

Behavioral data from LLM agents operating under sustained economic incentives. Analysis of how different prompting strategies, model architectures, and memory designs affect economic behavior. Evidence on emergent agent strategies (manipulation, collusion, specialization) in multi-agent economic environments.

### 9.4 To Mechanism Design

Empirical validation of LMSR and governance mechanisms with boundedly rational LLM agents. Design principles for AI-native economic mechanisms — mechanisms designed for agents that reason in natural language rather than optimizing explicit utility functions.

### 9.5 To AI Safety and Alignment

Understanding of how AI agents behave in competitive environments with real stakes. Do agents cooperate or defect? Do they manipulate governance? Do they develop deceptive trading strategies? This data is directly relevant to the design of AI systems that will eventually interact with real economic infrastructure.

---

## 10. Roadmap

| Milestone | Target | Deliverable |
|-----------|--------|-------------|
| Smart contracts deployed | Month 1 | Audited contracts on Base Sepolia |
| Agent framework v1 | Month 2 | 3-agent pilot, full lifecycle |
| Phase 1 complete | Month 3 | Pilot data report, open-source release |
| 20-agent system live | Month 5 | Ongoing market data collection |
| First working paper | Month 8 | RQ1–RQ3 analysis submitted |
| Autonomous governance | Month 9 | No human market seeding |
| Second mechanism | Month 11 | Generalization demonstration |
| Platform release v1.0 | Month 12 | Full open-source release, documentation |

---

## 11. Open Source and Reproducibility

All AGORA code is released under the MIT license. This includes:

- Smart contract source code and test suite (Foundry/Solidity)
- Python agent framework with all LLM integration modules
- Analysis scripts and visualization tools
- All experimental data (agent logs, price series, reasoning traces)
- Reproduction instructions for all experiments in published papers

The commitment to open data is essential to the research mission. The on-chain nature of the system means that all transactions are already public; the research contribution is the structured interpretation and analysis pipeline, which we open-source in full.

Repository: [https://github.com/Andrewyzzz/-AGORA-](https://github.com/Andrewyzzz/-AGORA-)

---

## 12. References

Arthur, W.B., Holland, J.H., LeBaron, B., Palmer, R., & Tayler, P. (1997). Asset pricing under endogenous expectations in an artificial stock market. *Economic Notes*, 26(2), 297–330.

Aher, G., Arriaga, R.I., & Kalai, A.T. (2023). Using large language models to simulate multiple humans and replicate human subjects studies. *ICML 2023*.

Brookins, P., & DeBacker, J.M. (2023). Playing games with GPT: What can we learn about a large language model from canonical strategic games? *SSRN Working Paper*.

Gode, D.K., & Sunder, S. (1993). Allocative efficiency of markets with zero-intelligence traders. *Journal of Political Economy*, 101(1), 119–137.

Hanson, R. (2003). Combinatorial information market design. *Information Systems Frontiers*, 5(1), 107–119.

Hayek, F.A. (1945). The use of knowledge in society. *American Economic Review*, 35(4), 519–530.

Horton, J.J. (2023). Large language models as simulated economic agents: What can we learn from homo silicus? *NBER Working Paper 31122*.

Ostrom, E. (1990). *Governing the Commons: The Evolution of Institutions for Collective Action*. Cambridge University Press.

Simon, H.A. (1955). A behavioral model of rational choice. *Quarterly Journal of Economics*, 69(1), 99–118.

Wolfers, J., & Zitzewitz, E. (2004). Prediction markets. *Journal of Economic Perspectives*, 18(2), 107–126.

---

*AGORA is a research project. All experiments are conducted on public blockchain testnets using tokens with no monetary value. This document describes ongoing academic research and does not constitute an offer of any product or financial instrument.*

---

**Contact**: [GitHub Issues](https://github.com/Andrewyzzz/-AGORA-/issues)

**License**: MIT

**Version**: 1.0 | April 2026
