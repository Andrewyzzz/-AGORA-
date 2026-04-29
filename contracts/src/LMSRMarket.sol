// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "./FixedPointMathLib.sol";
import "./ERC20.sol";
import "./OutcomeToken.sol";

/// @title LMSR Binary Prediction Market
/// @notice Implements Hanson's Logarithmic Market Scoring Rule for binary events
/// @dev Cost function: C(q1, q2) = b * ln(exp(q1/b) + exp(q2/b))
///      Price of YES:  p1 = exp(q1/b) / (exp(q1/b) + exp(q2/b))
///      Initial subsidy required: b * ln(2) — funded by MarketFactory
contract LMSRMarket {
    using FixedPointMathLib for int256;

    // ============ Enums ============

    enum Outcome { YES, NO }
    enum MarketState { ACTIVE, RESOLVED }

    // ============ State ============

    ERC20 public collateral;
    OutcomeToken public yesToken;
    OutcomeToken public noToken;

    int256 public qYes;  // Outstanding YES shares (WAD)
    int256 public qNo;   // Outstanding NO shares (WAD)
    int256 public b;     // Liquidity parameter (WAD)

    string public question;
    string public resolutionCriteria;
    uint256 public resolutionTimestamp;
    address public resolver;

    MarketState public state;
    Outcome public resolvedOutcome;
    uint256 public createdAt;

    // ============ Events ============

    event SharesPurchased(
        address indexed buyer,
        Outcome outcome,
        int256 amount,
        uint256 cost,
        uint256 newYesPrice,
        uint256 newNoPrice
    );

    event SharesSold(
        address indexed seller,
        Outcome outcome,
        int256 amount,
        uint256 payout,
        uint256 newYesPrice,
        uint256 newNoPrice
    );

    event MarketResolved(Outcome outcome, address indexed resolvedBy);
    event WinningsRedeemed(address indexed redeemer, uint256 amount);

    // ============ Constants ============

    int256 constant WAD = 1e18;
    int256 constant MAX_Q_OVER_B = 130e18;

    // ============ Constructor ============

    constructor(
        address _collateral,
        int256 _b,
        string memory _question,
        string memory _resolutionCriteria,
        uint256 _resolutionTimestamp,
        address _resolver
    ) {
        require(_b > 0, "LMSRMarket: b must be positive");
        require(_resolutionTimestamp > block.timestamp, "LMSRMarket: resolution must be in future");
        require(_resolver != address(0), "LMSRMarket: zero resolver");
        require(_collateral != address(0), "LMSRMarket: zero collateral");

        collateral = ERC20(_collateral);
        b = _b;
        question = _question;
        resolutionCriteria = _resolutionCriteria;
        resolutionTimestamp = _resolutionTimestamp;
        resolver = _resolver;
        state = MarketState.ACTIVE;
        createdAt = block.timestamp;

        yesToken = new OutcomeToken(
            string.concat("YES: ", _question),
            "YES",
            address(this)
        );
        noToken = new OutcomeToken(
            string.concat("NO: ", _question),
            "NO",
            address(this)
        );
    }

    // ============ Trading ============

    /// @notice Buy outcome tokens
    /// @param outcome YES or NO
    /// @param amount Number of tokens to buy (WAD)
    /// @return cost Collateral paid (WAD)
    function buy(Outcome outcome, int256 amount) external returns (uint256 cost) {
        require(state == MarketState.ACTIVE, "LMSRMarket: not active");
        require(amount > 0, "LMSRMarket: amount must be positive");

        int256 costBefore = _costFunction(qYes, qNo);

        if (outcome == Outcome.YES) {
            qYes += amount;
            require(qYes.wadDiv(b) < MAX_Q_OVER_B, "LMSRMarket: position too large");
        } else {
            qNo += amount;
            require(qNo.wadDiv(b) < MAX_Q_OVER_B, "LMSRMarket: position too large");
        }

        int256 costAfter = _costFunction(qYes, qNo);
        int256 deltaCost = costAfter - costBefore;
        require(deltaCost > 0, "LMSRMarket: invalid cost");

        cost = uint256(deltaCost);

        require(
            collateral.transferFrom(msg.sender, address(this), cost),
            "LMSRMarket: collateral transfer failed"
        );

        if (outcome == Outcome.YES) {
            yesToken.mint(msg.sender, uint256(amount));
        } else {
            noToken.mint(msg.sender, uint256(amount));
        }

        emit SharesPurchased(msg.sender, outcome, amount, cost, _getYesPrice(), _getNoPrice());
    }

    /// @notice Sell outcome tokens back to the market
    /// @param outcome YES or NO
    /// @param amount Number of tokens to sell (WAD)
    /// @return payout Collateral received (WAD)
    function sell(Outcome outcome, int256 amount) external returns (uint256 payout) {
        require(state == MarketState.ACTIVE, "LMSRMarket: not active");
        require(amount > 0, "LMSRMarket: amount must be positive");

        if (outcome == Outcome.YES) {
            require(qYes >= amount, "LMSRMarket: insufficient YES shares outstanding");
        } else {
            require(qNo >= amount, "LMSRMarket: insufficient NO shares outstanding");
        }

        int256 costBefore = _costFunction(qYes, qNo);

        if (outcome == Outcome.YES) {
            qYes -= amount;
        } else {
            qNo -= amount;
        }

        int256 costAfter = _costFunction(qYes, qNo);
        int256 deltaRefund = costBefore - costAfter;
        require(deltaRefund > 0, "LMSRMarket: invalid payout");

        payout = uint256(deltaRefund);

        if (outcome == Outcome.YES) {
            yesToken.burn(msg.sender, uint256(amount));
        } else {
            noToken.burn(msg.sender, uint256(amount));
        }

        require(
            collateral.transfer(msg.sender, payout),
            "LMSRMarket: collateral transfer failed"
        );

        emit SharesSold(msg.sender, outcome, amount, payout, _getYesPrice(), _getNoPrice());
    }

    // ============ Resolution ============

    /// @notice Resolve the market. Only callable by the designated resolver after the resolution timestamp.
    function resolve(Outcome outcome) external {
        require(msg.sender == resolver, "LMSRMarket: only resolver");
        require(state == MarketState.ACTIVE, "LMSRMarket: already resolved");
        require(block.timestamp >= resolutionTimestamp, "LMSRMarket: too early");

        state = MarketState.RESOLVED;
        resolvedOutcome = outcome;

        emit MarketResolved(outcome, msg.sender);
    }

    /// @notice Redeem winning tokens for collateral (1:1)
    function redeem() external {
        require(state == MarketState.RESOLVED, "LMSRMarket: not resolved");

        uint256 payout;

        if (resolvedOutcome == Outcome.YES) {
            payout = yesToken.balanceOf(msg.sender);
            require(payout > 0, "LMSRMarket: no winning tokens");
            yesToken.burn(msg.sender, payout);
        } else {
            payout = noToken.balanceOf(msg.sender);
            require(payout > 0, "LMSRMarket: no winning tokens");
            noToken.burn(msg.sender, payout);
        }

        require(
            collateral.transfer(msg.sender, payout),
            "LMSRMarket: collateral transfer failed"
        );

        emit WinningsRedeemed(msg.sender, payout);
    }

    // ============ View Functions ============

    /// @notice Get current price of an outcome (WAD, range 0 to 1e18)
    function getPrice(Outcome outcome) external view returns (uint256) {
        return outcome == Outcome.YES ? _getYesPrice() : _getNoPrice();
    }

    /// @notice Get cost to buy a given amount of an outcome
    function getCost(Outcome outcome, int256 amount) external view returns (uint256) {
        int256 costBefore = _costFunction(qYes, qNo);
        int256 newQYes = qYes;
        int256 newQNo = qNo;

        if (outcome == Outcome.YES) {
            newQYes += amount;
        } else {
            newQNo += amount;
        }

        int256 costAfter = _costFunction(newQYes, newQNo);
        int256 delta = costAfter - costBefore;
        require(delta >= 0, "LMSRMarket: negative cost");
        return uint256(delta);
    }

    /// @notice Get payout for selling a given amount of an outcome
    function getSellPayout(Outcome outcome, int256 amount) external view returns (uint256) {
        int256 costBefore = _costFunction(qYes, qNo);
        int256 newQYes = qYes;
        int256 newQNo = qNo;

        if (outcome == Outcome.YES) {
            newQYes -= amount;
        } else {
            newQNo -= amount;
        }

        int256 costAfter = _costFunction(newQYes, newQNo);
        int256 delta = costBefore - costAfter;
        require(delta >= 0, "LMSRMarket: negative payout");
        return uint256(delta);
    }

    /// @notice Get all market state in a single call (for agent framework efficiency)
    function getMarketInfo()
        external
        view
        returns (
            string memory _question,
            string memory _resolutionCriteria,
            uint256 _resolutionTimestamp,
            address _resolver,
            uint256 _yesPrice,
            uint256 _noPrice,
            int256 _qYes,
            int256 _qNo,
            int256 _b,
            MarketState _state,
            Outcome _resolvedOutcome,
            uint256 _collateralBalance
        )
    {
        return (
            question,
            resolutionCriteria,
            resolutionTimestamp,
            resolver,
            _getYesPrice(),
            _getNoPrice(),
            qYes,
            qNo,
            b,
            state,
            resolvedOutcome,
            collateral.balanceOf(address(this))
        );
    }

    // ============ Internal ============

    /// @dev LMSR cost function: C(q1, q2) = b * ln(exp(q1/b) + exp(q2/b))
    function _costFunction(int256 q1, int256 q2) internal view returns (int256) {
        int256 exp1 = FixedPointMathLib.wadExp(q1.wadDiv(b));
        int256 exp2 = FixedPointMathLib.wadExp(q2.wadDiv(b));
        return b.wadMul(FixedPointMathLib.wadLn(exp1 + exp2));
    }

    function _getYesPrice() internal view returns (uint256) {
        int256 expYes = FixedPointMathLib.wadExp(qYes.wadDiv(b));
        int256 expNo  = FixedPointMathLib.wadExp(qNo.wadDiv(b));
        return uint256(expYes.wadDiv(expYes + expNo));
    }

    function _getNoPrice() internal view returns (uint256) {
        int256 expYes = FixedPointMathLib.wadExp(qYes.wadDiv(b));
        int256 expNo  = FixedPointMathLib.wadExp(qNo.wadDiv(b));
        return uint256(expNo.wadDiv(expYes + expNo));
    }
}
