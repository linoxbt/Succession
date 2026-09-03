// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

/// @notice The subset of ERC-20 the escrow needs. B20 and USDC both satisfy it.
interface IERC20 {
    function transfer(address to, uint256 amount) external returns (bool);
    function transferFrom(address from, address to, uint256 amount) external returns (bool);
    function balanceOf(address account) external view returns (uint256);
    function allowance(address owner, address spender) external view returns (uint256);
}
