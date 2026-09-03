// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

/// @notice The subset of the ERC-8004 Identity Registry this contract uses.
///
/// ERC-8004 identifies each agent by an ERC-721-style token — `agentId` is the
/// `tokenId` — whose `agentURI` resolves to the agent's registration file.
/// Transferring the token transfers the identity, which is the whole primitive
/// the Succession transfer step is built on. Nothing here is Succession-specific;
/// it is plain ERC-721.
interface IIdentityRegistry {
    function ownerOf(uint256 agentId) external view returns (address);
    function transferFrom(address from, address to, uint256 agentId) external;
    function getApproved(uint256 agentId) external view returns (address);
    function isApprovedForAll(address owner, address operator) external view returns (bool);
}
