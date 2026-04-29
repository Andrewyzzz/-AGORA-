// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "forge-std/Test.sol";
import "../src/LMSRMarket.sol";
import "../src/MarketFactory.sol";
import "../src/MockCollateral.sol";
import "../src/OutcomeToken.sol";
import "../src/FixedPointMathLib.sol";

contract LMSRMarketTest is Test {
    MockCollateral collateral;
    MarketFactory factory;
    LMSRMarket market;

    address alice   = makeAddr("alice");
    address bob     = makeAddr("bob");
    address charlie = makeAddr("charlie");

    int256 constant B = 100e18;

    function setUp() public {
        collateral = new MockCollateral();
        factory    = new MarketFactory(address(collateral));

        address marketAddr = factory.createMarket(
            B,
            "Will BTC exceed 150000 USD by Dec 31, 2026?",
            "Resolves YES if BTC/USD on Coinbase exceeds 150000.00 before Dec 31, 2026 23:59:59 UTC",
            block.timestamp + 365 days,
            address(this)
        );
        market = LMSRMarket(marketAddr);

        collateral.mint(alice,   10_000e18);
        collateral.mint(bob,     10_000e18);
        collateral.mint(charlie, 10_000e18);

        vm.prank(alice);   collateral.approve(address(market), type(uint256).max);
        vm.prank(bob);     collateral.approve(address(market), type(uint256).max);
        vm.prank(charlie); collateral.approve(address(market), type(uint256).max);
    }

    // ============ Initial State ============

    function test_initialPricesAreEqual() public view {
        uint256 yesPrice = market.getPrice(LMSRMarket.Outcome.YES);
        uint256 noPrice  = market.getPrice(LMSRMarket.Outcome.NO);
        assertApproxEqAbs(yesPrice, 0.5e18, 1e15, "YES price should be ~0.5");
        assertApproxEqAbs(noPrice,  0.5e18, 1e15, "NO price should be ~0.5");
    }

    function test_initialPricesSumToOne() public view {
        uint256 yesPrice = market.getPrice(LMSRMarket.Outcome.YES);
        uint256 noPrice  = market.getPrice(LMSRMarket.Outcome.NO);
        assertApproxEqAbs(yesPrice + noPrice, 1e18, 1e15, "Prices should sum to 1");
    }

    function test_marketCreatedWithCorrectLiquidity() public view {
        uint256 balance = collateral.balanceOf(address(market));
        uint256 expectedSubsidy = uint256(
            FixedPointMathLib.wadMul(B, FixedPointMathLib.wadLn(2e18))
        );
        assertEq(balance, expectedSubsidy, "Initial liquidity should be b * ln(2)");
    }

    // ============ Trading ============

    function test_buyYesIncreasesYesPrice() public {
        uint256 priceBefore = market.getPrice(LMSRMarket.Outcome.YES);
        vm.prank(alice);
        market.buy(LMSRMarket.Outcome.YES, 10e18);
        uint256 priceAfter = market.getPrice(LMSRMarket.Outcome.YES);
        assertGt(priceAfter, priceBefore, "YES price should increase after buying YES");
    }

    function test_buyYesDecreasesNoPrice() public {
        uint256 priceBefore = market.getPrice(LMSRMarket.Outcome.NO);
        vm.prank(alice);
        market.buy(LMSRMarket.Outcome.YES, 10e18);
        uint256 priceAfter = market.getPrice(LMSRMarket.Outcome.NO);
        assertLt(priceAfter, priceBefore, "NO price should decrease after buying YES");
    }

    function test_pricesSumToOneAfterTrades() public {
        vm.prank(alice);   market.buy(LMSRMarket.Outcome.YES, 50e18);
        vm.prank(bob);     market.buy(LMSRMarket.Outcome.NO,  30e18);
        vm.prank(charlie); market.buy(LMSRMarket.Outcome.YES, 20e18);

        uint256 yesPrice = market.getPrice(LMSRMarket.Outcome.YES);
        uint256 noPrice  = market.getPrice(LMSRMarket.Outcome.NO);
        assertApproxEqAbs(yesPrice + noPrice, 1e18, 1e15, "Prices should still sum to 1");
    }

    function test_completeSetCostsExactlyOne() public {
        vm.startPrank(alice);
        uint256 yesCost = market.buy(LMSRMarket.Outcome.YES, 1e18);
        uint256 noCost  = market.buy(LMSRMarket.Outcome.NO,  1e18);
        vm.stopPrank();
        assertApproxEqAbs(yesCost + noCost, 1e18, 1e15, "1 YES + 1 NO should cost ~1 token");
    }

    function test_buyMintsCorrectTokens() public {
        vm.prank(alice);
        market.buy(LMSRMarket.Outcome.YES, 5e18);
        assertEq(market.yesToken().balanceOf(alice), 5e18, "Alice should have 5 YES tokens");
        assertEq(market.noToken().balanceOf(alice),  0,    "Alice should have 0 NO tokens");
    }

    function test_sellRoundTripPreservesBalance() public {
        vm.startPrank(alice);
        market.buy(LMSRMarket.Outcome.YES, 10e18);
        market.sell(LMSRMarket.Outcome.YES, 10e18);
        vm.stopPrank();
        assertApproxEqAbs(collateral.balanceOf(alice), 10_000e18, 1e15, "Round-trip should preserve balance");
    }

    function test_getCostMatchesActualCost() public {
        uint256 estimatedCost = market.getCost(LMSRMarket.Outcome.YES, 10e18);
        vm.prank(alice);
        uint256 actualCost = market.buy(LMSRMarket.Outcome.YES, 10e18);
        assertEq(estimatedCost, actualCost, "Estimated cost should match actual cost");
    }

    // ============ Resolution ============

    function test_resolveAndRedeem() public {
        vm.prank(alice); market.buy(LMSRMarket.Outcome.YES, 10e18);
        vm.prank(bob);   market.buy(LMSRMarket.Outcome.NO,  5e18);

        uint256 aliceBefore = collateral.balanceOf(alice);

        vm.warp(block.timestamp + 366 days);
        market.resolve(LMSRMarket.Outcome.YES);

        vm.prank(alice);
        market.redeem();

        assertEq(collateral.balanceOf(alice) - aliceBefore, 10e18, "Alice should receive 10 collateral");

        vm.prank(bob);
        vm.expectRevert("LMSRMarket: no winning tokens");
        market.redeem();
    }

    function test_cannotTradeAfterResolution() public {
        vm.warp(block.timestamp + 366 days);
        market.resolve(LMSRMarket.Outcome.YES);

        vm.prank(alice);
        vm.expectRevert("LMSRMarket: not active");
        market.buy(LMSRMarket.Outcome.YES, 1e18);
    }

    function test_cannotResolveBeforeTimestamp() public {
        vm.expectRevert("LMSRMarket: too early");
        market.resolve(LMSRMarket.Outcome.YES);
    }

    function test_onlyResolverCanResolve() public {
        vm.warp(block.timestamp + 366 days);
        vm.prank(alice);
        vm.expectRevert("LMSRMarket: only resolver");
        market.resolve(LMSRMarket.Outcome.YES);
    }

    // ============ Price Accuracy ============

    function test_smallTradesCostPositive() public {
        vm.prank(alice);
        uint256 cost = market.buy(LMSRMarket.Outcome.YES, 0.001e18);
        assertGt(cost, 0, "Cost should be positive for any trade");
    }

    function test_largeTradesMovePriceSignificantly() public {
        vm.prank(alice);
        market.buy(LMSRMarket.Outcome.YES, 200e18);
        uint256 yesPrice = market.getPrice(LMSRMarket.Outcome.YES);
        // With b=100 and qYes=200, price ≈ exp(2)/(exp(2)+1) ≈ 0.88
        assertGt(yesPrice, 0.85e18, "Large buy should push price above 85%");
        assertLt(yesPrice, 0.92e18, "Price should be within expected range");
    }

    // ============ Market Info ============

    function test_getMarketInfoReturnsCorrectData() public {
        vm.prank(alice);
        market.buy(LMSRMarket.Outcome.YES, 25e18);

        (
            string memory q,,,, uint256 yP, uint256 nP,
            int256 qY, int256 qN, int256 bVal,
            LMSRMarket.MarketState s,,
        ) = market.getMarketInfo();

        assertEq(keccak256(bytes(q)), keccak256(bytes("Will BTC exceed 150000 USD by Dec 31, 2026?")));
        assertGt(yP, nP, "YES price should be higher after YES purchases");
        assertEq(qY, 25e18, "qYes should be 25");
        assertEq(qN, 0,     "qNo should be 0");
        assertEq(bVal, B,   "b should match");
        assertEq(uint256(s), uint256(LMSRMarket.MarketState.ACTIVE));
    }

    // ============ Factory ============

    function test_factoryTracksMarkets() public {
        assertEq(factory.getMarketCount(), 1, "Should have 1 market");
        assertTrue(factory.isMarket(address(market)), "Market should be registered");

        factory.createMarket(
            50e18,
            "Will it rain tomorrow?",
            "Resolves YES if >1mm precipitation recorded at HKO",
            block.timestamp + 1 days,
            address(this)
        );
        assertEq(factory.getMarketCount(), 2, "Should have 2 markets");
    }
}
