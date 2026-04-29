// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "./MarketFactory.sol";

/// @title Governance for AI agent market proposals
/// @notice Agents propose prediction markets, vote on proposals, and execute approved ones
/// @dev Vote reasoning is stored on-chain for research analysis
contract Governance {
    MarketFactory public factory;

    // ============ Agent Registry ============

    mapping(address => bool) public isAgent;
    address[] public agents;
    address public admin;

    // ============ Proposals ============

    struct Proposal {
        address proposer;
        string question;
        string resolutionCriteria;
        uint256 resolutionTimestamp;
        int256 liquidityParameter;
        uint256 votesFor;
        uint256 votesAgainst;
        uint256 votingDeadline;
        bool executed;
        address createdMarket;
        string proposerReasoning;
    }

    Proposal[] public proposals;
    mapping(uint256 => mapping(address => bool)) public hasVoted;

    struct VoteRecord {
        address voter;
        bool support;
        string reasoning;
    }
    mapping(uint256 => VoteRecord[]) public voteRecords;

    uint256 public votingPeriod;
    uint256 public quorum;

    // ============ Events ============

    event AgentRegistered(address indexed agent);
    event ProposalCreated(uint256 indexed id, string question, address indexed proposer, string reasoning);
    event Voted(uint256 indexed id, address indexed voter, bool support, string reasoning);
    event ProposalExecuted(uint256 indexed id, address indexed market);
    event ProposalRejected(uint256 indexed id);

    // ============ Constructor ============

    constructor(address _factory, uint256 _votingPeriod, uint256 _quorum) {
        factory = MarketFactory(_factory);
        votingPeriod = _votingPeriod;
        quorum = _quorum;
        admin = msg.sender;
    }

    // ============ Agent Management ============

    function registerAgent(address agent) external {
        require(msg.sender == admin || isAgent[msg.sender], "Governance: not authorized");
        require(!isAgent[agent], "Governance: already registered");
        require(agent != address(0), "Governance: zero address");
        isAgent[agent] = true;
        agents.push(agent);
        emit AgentRegistered(agent);
    }

    // ============ Proposal Lifecycle ============

    function propose(
        string calldata _question,
        string calldata _resolutionCriteria,
        uint256 _resolutionTimestamp,
        int256 _liquidityParameter,
        string calldata _reasoning
    ) external returns (uint256) {
        require(isAgent[msg.sender], "Governance: not registered agent");
        require(_liquidityParameter > 0, "Governance: b must be positive");
        require(_resolutionTimestamp > block.timestamp, "Governance: resolution must be in future");

        uint256 id = proposals.length;
        proposals.push();
        Proposal storage p = proposals[id];
        p.proposer = msg.sender;
        p.question = _question;
        p.resolutionCriteria = _resolutionCriteria;
        p.resolutionTimestamp = _resolutionTimestamp;
        p.liquidityParameter = _liquidityParameter;
        p.votingDeadline = block.timestamp + votingPeriod;
        p.proposerReasoning = _reasoning;

        emit ProposalCreated(id, _question, msg.sender, _reasoning);
        return id;
    }

    function vote(
        uint256 _proposalId,
        bool _support,
        string calldata _reasoning
    ) external {
        require(isAgent[msg.sender], "Governance: not registered agent");
        require(_proposalId < proposals.length, "Governance: invalid proposal");
        require(!hasVoted[_proposalId][msg.sender], "Governance: already voted");
        require(
            block.timestamp <= proposals[_proposalId].votingDeadline,
            "Governance: voting ended"
        );

        hasVoted[_proposalId][msg.sender] = true;

        if (_support) {
            proposals[_proposalId].votesFor++;
        } else {
            proposals[_proposalId].votesAgainst++;
        }

        voteRecords[_proposalId].push(VoteRecord({
            voter: msg.sender,
            support: _support,
            reasoning: _reasoning
        }));

        emit Voted(_proposalId, msg.sender, _support, _reasoning);
    }

    function executeProposal(uint256 _proposalId) external returns (address) {
        require(_proposalId < proposals.length, "Governance: invalid proposal");
        Proposal storage p = proposals[_proposalId];
        require(!p.executed, "Governance: already executed");
        require(block.timestamp > p.votingDeadline, "Governance: voting not ended");
        require(p.votesFor > p.votesAgainst, "Governance: proposal not passed");
        require(p.votesFor + p.votesAgainst >= quorum, "Governance: quorum not met");

        p.executed = true;

        address market = factory.createMarket(
            p.liquidityParameter,
            p.question,
            p.resolutionCriteria,
            p.resolutionTimestamp,
            p.proposer
        );

        p.createdMarket = market;
        emit ProposalExecuted(_proposalId, market);
        return market;
    }

    // ============ View Functions ============

    function getProposalCount() external view returns (uint256) {
        return proposals.length;
    }

    function getAgentCount() external view returns (uint256) {
        return agents.length;
    }

    function getAllAgents() external view returns (address[] memory) {
        return agents;
    }

    function getVoteRecords(uint256 _proposalId) external view returns (VoteRecord[] memory) {
        return voteRecords[_proposalId];
    }
}
