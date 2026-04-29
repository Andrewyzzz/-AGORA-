// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "./FixedPointMathLib.sol";
import "./MockCollateral.sol";
import "./LMSRMarket.sol";

/// @title Factory for creating LMSR prediction markets
/// @notice Deploys new markets and funds their initial liquidity via MockCollateral minting
/// @dev Initial liquidity = b * ln(2), minted for free on testnet
contract MarketFactory {
    using FixedPointMathLib for int256;

    MockCollateral public collateral;
    address[] public markets;
    mapping(address => bool) public isMarket;

    event MarketCreated(
        address indexed market,
        string question,
        int256 liquidityParameter,
        uint256 resolutionTimestamp,
        address resolver,
        uint256 initialLiquidity
    );

    constructor(address _collateral) {
        collateral = MockCollateral(_collateral);
    }

    /// @notice Create a new binary prediction market
    /// @param _b Liquidity parameter (WAD). Higher = more liquid.
    ///           Recommended: 100e18 for research, 1000e18 for deeper markets.
    function createMarket(
        int256 _b,
        string calldata _question,
        string calldata _resolutionCriteria,
        uint256 _resolutionTimestamp,
        address _resolver
    ) external returns (address) {
        LMSRMarket market = new LMSRMarket(
            address(collateral),
            _b,
            _question,
            _resolutionCriteria,
            _resolutionTimestamp,
            _resolver
        );

        // Fund initial liquidity: b * ln(2) — the maximum possible loss
        int256 initialCostWad = _b.wadMul(FixedPointMathLib.wadLn(2e18));
        uint256 initialCost = uint256(initialCostWad);
        collateral.mint(address(market), initialCost);

        markets.push(address(market));
        isMarket[address(market)] = true;

        emit MarketCreated(
            address(market),
            _question,
            _b,
            _resolutionTimestamp,
            _resolver,
            initialCost
        );

        return address(market);
    }

    function getMarketCount() external view returns (uint256) {
        return markets.length;
    }

    function getAllMarkets() external view returns (address[] memory) {
        return markets;
    }
}
