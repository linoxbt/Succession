// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

/// @notice A minimal ERC-721 stand-in for the ERC-8004 Identity Registry.
///
/// Only what ListingContract touches: ownership, single-token approval,
/// operator approval, and transfer. `agentURI` is carried because ERC-8004
/// resolves it to the agent's registration file, and a transferred identity
/// that lost its URI would not be the same agent on the other side.
contract MockIdentityRegistry {
    mapping(uint256 => address) private _owners;
    mapping(uint256 => address) private _tokenApprovals;
    mapping(address => mapping(address => bool)) private _operatorApprovals;
    mapping(uint256 => string) public agentURI;

    event Transfer(address indexed from, address indexed to, uint256 indexed tokenId);
    event Approval(address indexed owner, address indexed approved, uint256 indexed tokenId);

    function register(address to, uint256 agentId, string calldata uri) external {
        require(_owners[agentId] == address(0), "already registered");
        _owners[agentId] = to;
        agentURI[agentId] = uri;
        emit Transfer(address(0), to, agentId);
    }

    function ownerOf(uint256 agentId) public view returns (address) {
        address owner = _owners[agentId];
        require(owner != address(0), "no such agent");
        return owner;
    }

    function approve(address to, uint256 agentId) external {
        require(ownerOf(agentId) == msg.sender, "not owner");
        _tokenApprovals[agentId] = to;
        emit Approval(msg.sender, to, agentId);
    }

    function getApproved(uint256 agentId) external view returns (address) {
        return _tokenApprovals[agentId];
    }

    function setApprovalForAll(address operator, bool approved) external {
        _operatorApprovals[msg.sender][operator] = approved;
    }

    function isApprovedForAll(address owner, address operator) external view returns (bool) {
        return _operatorApprovals[owner][operator];
    }

    function transferFrom(address from, address to, uint256 agentId) external {
        require(ownerOf(agentId) == from, "wrong owner");
        require(to != address(0), "zero recipient");
        require(
            msg.sender == from || _tokenApprovals[agentId] == msg.sender
                || _operatorApprovals[from][msg.sender],
            "not approved"
        );
        delete _tokenApprovals[agentId];
        _owners[agentId] = to;
        emit Transfer(from, to, agentId);
    }
}
