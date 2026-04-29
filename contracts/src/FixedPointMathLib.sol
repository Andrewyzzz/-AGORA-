// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import {wadExp as _wadExp, wadLn as _wadLn, wadMul as _wadMul, wadDiv as _wadDiv} from
    "../lib/solmate/src/utils/SignedWadMath.sol";

/// @title Fixed-point math wrapper for LMSR calculations
/// @notice Thin library wrapper around Solmate's audited SignedWadMath free functions
library FixedPointMathLib {
    int256 internal constant WAD = 1e18;

    function wadMul(int256 x, int256 y) internal pure returns (int256) {
        return _wadMul(x, y);
    }

    function wadDiv(int256 x, int256 y) internal pure returns (int256) {
        return _wadDiv(x, y);
    }

    function wadExp(int256 x) internal pure returns (int256) {
        return _wadExp(x);
    }

    function wadLn(int256 x) internal pure returns (int256) {
        return _wadLn(x);
    }
}
