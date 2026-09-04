// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

/// @notice An ERC-20 that quietly keeps a cut of every transfer.
///
/// Plenty of real tokens do this, and a contract that assumes the amount it
/// asked for is the amount that arrived will later pay one seller out of
/// another listing's escrow. `ListingContract.buy` measures the balance delta
/// and rejects the shortfall; this token is what proves it does.
contract FeeOnTransferToken {
    string public name = "Fee On Transfer";
    string public symbol = "FEE";
    uint8 public decimals = 6;

    /// @dev Basis points withheld on every transfer.
    uint256 public feeBps = 100;

    mapping(address => uint256) public balanceOf;
    mapping(address => mapping(address => uint256)) public allowance;

    event Transfer(address indexed from, address indexed to, uint256 value);
    event Approval(address indexed owner, address indexed spender, uint256 value);

    function setFeeBps(uint256 bps) external {
        feeBps = bps;
    }

    function mint(address to, uint256 amount) external {
        balanceOf[to] += amount;
        emit Transfer(address(0), to, amount);
    }

    function approve(address spender, uint256 amount) external returns (bool) {
        allowance[msg.sender][spender] = amount;
        emit Approval(msg.sender, spender, amount);
        return true;
    }

    function _move(address from, address to, uint256 amount) private {
        require(balanceOf[from] >= amount, "insufficient balance");
        uint256 fee = (amount * feeBps) / 10_000;
        balanceOf[from] -= amount;
        balanceOf[to] += amount - fee;
        emit Transfer(from, to, amount - fee);
    }

    function transfer(address to, uint256 amount) external returns (bool) {
        _move(msg.sender, to, amount);
        return true;
    }

    function transferFrom(address from, address to, uint256 amount) external returns (bool) {
        uint256 allowed = allowance[from][msg.sender];
        require(allowed >= amount, "insufficient allowance");
        if (allowed != type(uint256).max) allowance[from][msg.sender] = allowed - amount;
        _move(from, to, amount);
        return true;
    }
}
