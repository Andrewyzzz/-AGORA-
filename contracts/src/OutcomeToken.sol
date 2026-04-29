// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "./ERC20.sol";

/// @title Outcome token (YES or NO) for a prediction market
/// @notice Only the parent market contract can mint and burn
contract OutcomeToken is ERC20 {
    address public immutable market;

    modifier onlyMarket() {
        require(msg.sender == market, "OutcomeToken: caller is not market");
        _;
    }

    constructor(
        string memory _name,
        string memory _symbol,
        address _market
    ) ERC20(_name, _symbol) {
        require(_market != address(0), "OutcomeToken: zero market address");
        market = _market;
    }

    function mint(address to, uint256 amount) external onlyMarket {
        _mint(to, amount);
    }

    function burn(address from, uint256 amount) external onlyMarket {
        _burn(from, amount);
    }
}
