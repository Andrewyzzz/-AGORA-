// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "./ERC20.sol";

/// @title Mock collateral token for AGORA research testnet
/// @notice Anyone can mint — intentional for research purposes
contract MockCollateral is ERC20 {
    constructor() ERC20("AGORA Collateral", "AGORA") {}

    /// @notice Mint tokens to any address. Testnet only — no access control.
    function mint(address to, uint256 amount) external {
        _mint(to, amount);
    }
}
