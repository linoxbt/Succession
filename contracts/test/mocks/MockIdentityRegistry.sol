// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

/// @notice A minimal ERC-721 stand-in for the ERC-8004 Identity Registry.
///
/// Only what ListingContract touches: ownership, single-token approval,
/// operator approval, and transfer. `agentURI` is carried because ERC-8004
/// resolves it to the agent's registration file, and a transferred identity
/// that lost its URI would not be the same agent on the other side.
///
/// @dev This exists for local runs and for the py-evm suite. The real thing is
///      the ERC-8004 registry deployed on Base Sepolia at
///      `0x7177a6867296406881E20d6647232314736Dd09A`, which the deploy script
///      now points at by default; see `succession/erc8004.py`. Both
///      `register` overloads below are present so a local run exercises the
///      *same* call the real registry serves — a stand-in whose interface
///      differs from production is a stand-in that hides integration bugs
///      until the day they cost the most.
contract MockIdentityRegistry {
    mapping(uint256 => address) private _owners;
    mapping(uint256 => address) private _tokenApprovals;
    mapping(address => mapping(address => bool)) private _operatorApprovals;
    mapping(uint256 => string) public agentURI;

    /// @dev Mint counter for the ERC-8004 `register(string)` overload.
    uint256 private _nextAgentId = 1;

    event Transfer(address indexed from, address indexed to, uint256 indexed tokenId);
    event Approval(address indexed owner, address indexed approved, uint256 indexed tokenId);
    event Registered(uint256 indexed agentId, string agentURI, address indexed owner);

    /// @notice ERC-8004 `register`: permissionless, mints to the caller.
    function register(string calldata uri) external returns (uint256 agentId) {
        agentId = _nextAgentId++;
        _owners[agentId] = msg.sender;
        agentURI[agentId] = uri;
        emit Transfer(address(0), msg.sender, agentId);
        emit Registered(agentId, uri, msg.sender);
    }

    /// @notice Test-only: mint a chosen `agentId` to a chosen owner.
    /// @dev The suite pins specific ids (0417, 1183) to match the spec's
    ///      worked example, which `register(string)` cannot do because it
    ///      allocates sequentially.
    function register(address to, uint256 agentId, string calldata uri) external {
        require(_owners[agentId] == address(0), "already registered");
        if (agentId >= _nextAgentId) _nextAgentId = agentId + 1;
        _owners[agentId] = to;
        agentURI[agentId] = uri;
        emit Transfer(address(0), to, agentId);
        emit Registered(agentId, uri, to);
    }

    /// @notice ERC-721 introspection, so the stand-in answers the same probe
    ///         the real registry does.
    function supportsInterface(bytes4 interfaceId) external pure returns (bool) {
        return interfaceId == 0x80ac58cd || interfaceId == 0x01ffc9a7;
    }

    function tokenURI(uint256 agentId) external view returns (string memory) {
        require(_owners[agentId] != address(0), "no such agent");
        return agentURI[agentId];
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
