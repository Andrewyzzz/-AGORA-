// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "forge-std/Script.sol";
import "../src/MockCollateral.sol";
import "../src/MarketFactory.sol";
import "../src/Governance.sol";

contract DeployScript is Script {
    function run() external {
        uint256 deployerPrivateKey = vm.envUint("PRIVATE_KEY");
        vm.startBroadcast(deployerPrivateKey);

        // 1. Deploy collateral token
        MockCollateral collateral = new MockCollateral();
        console.log("MockCollateral:", address(collateral));

        // 2. Deploy market factory
        MarketFactory factory = new MarketFactory(address(collateral));
        console.log("MarketFactory:", address(factory));

        // 3. Deploy governance
        //    Voting period: 1 hour | Quorum: 2 votes minimum
        Governance governance = new Governance(
            address(factory),
            1 hours,
            2
        );
        console.log("Governance:", address(governance));

        // 4. Create an initial test market (BTC price question)
        address testMarket = factory.createMarket(
            100e18,
            "Will BTC exceed 150000 USD by December 31, 2026?",
            "Resolves YES if the Bitcoin/USD spot price on Coinbase exceeds 150000.00 at any point before December 31, 2026 23:59:59 UTC. Primary source: Coinbase BTC-USD. Fallback: Binance BTC/USDT.",
            block.timestamp + 180 days,
            msg.sender
        );
        console.log("Test Market:", testMarket);

        // 5. Pre-fund three agent wallets with collateral
        //    Replace with actual agent addresses after generating in Python
        address agent1 = 0x1111111111111111111111111111111111111111;
        address agent2 = 0x2222222222222222222222222222222222222222;
        address agent3 = 0x3333333333333333333333333333333333333333;

        collateral.mint(agent1, 100_000e18);
        collateral.mint(agent2, 100_000e18);
        collateral.mint(agent3, 100_000e18);
        console.log("Funded 3 agent wallets with 100,000 AGORA each");

        vm.stopBroadcast();
    }
}
