// SPDX-License-Identifier: MIT
pragma solidity ^0.8.28;

/// Test-only deployed wallet for the authenticated buyer claim path.
contract SigningWallet {
    address public immutable owner;
    constructor(address owner_) { owner = owner_; }
    function execute(address target, bytes calldata data) external returns (bytes memory) {
        require(msg.sender == owner, "owner only");
        (bool ok, bytes memory result) = target.call(data);
        require(ok, "call failed");
        return result;
    }
    function isValidSignature(bytes32 digest, bytes calldata signature) external view returns (bytes4) {
        if (signature.length != 65) return 0xffffffff;
        bytes32 r; bytes32 s; uint8 v;
        assembly {
            r := calldataload(signature.offset)
            s := calldataload(add(signature.offset, 32))
            v := byte(0, calldataload(add(signature.offset, 64)))
        }
        return ecrecover(digest, v, r, s) == owner ? bytes4(0x1626ba7e) : bytes4(0xffffffff);
    }
}
