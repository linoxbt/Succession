// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {IERC20} from "./interfaces/IERC20.sol";
import {IIdentityRegistry} from "./interfaces/IIdentityRegistry.sol";

/// @title Succession ListingContract
/// @notice Escrows payment for an agent's memory, and releases it only against a
///         hash that matches what the seller committed to at listing time — in
///         the same transaction that moves the agent's ERC-8004 identity and
///         seals the seller's copy.
///
/// @dev What "atomic" means here, precisely.
///
/// A single transaction cannot span this chain and an off-chain memory store, so
/// the guarantee is built by ordering rather than claimed by assertion:
///
///   1. `list` — the seller commits to a hash and attests to it with their agent
///      key. Nothing has moved.
///   2. `buy` — the buyer's funds enter escrow. Still nothing has moved; the
///      seller cannot touch the money and the buyer holds no identity.
///   3. off-chain — the package is delivered, imported into the buyer's fresh
///      tenant, and re-hashed there.
///   4. `confirmTransfer` — payment release, identity transfer, and the sealed
///      flag all happen in *this one transaction*. All of them, or none.
///
/// Step 4 is where atomicity actually lives, and it is real because it is one
/// EVM transaction. Every state before it is safe to abandon: `refund` and
/// `reclaimExpired` return the buyer's funds and leave the seller exactly as
/// they were.
///
/// @dev Known adversarial edge, stated rather than hidden.
///
/// `confirmTransfer` is called by the buyer, who asserts the hash they derived
/// from what they received. A dishonest buyer can therefore submit a wrong hash,
/// trigger the automatic refund, and keep the decrypted package. This contract
/// does not solve that, and no amount of on-chain logic can: the chain cannot
/// see the delivered bytes. The designed answer is the `arbiter` role below —
/// the hook for the Evaluator-style third-party agent that ACP already uses for
/// job quality, applied here to delivery integrity. An arbiter can independently
/// re-derive the root and confirm. Wiring a real evaluator agent into that role
/// is roadmap; the role exists now so the contract does not need redeploying to
/// gain one.
contract ListingContract {
    // -----------------------------------------------------------------
    // Types
    // -----------------------------------------------------------------

    enum State {
        None,
        Open,
        Escrowed,
        Confirmed,
        Refunded
    }

    struct Listing {
        address seller;
        address buyer;
        uint256 agentId;
        bytes32 hashCommitment;
        uint256 price;
        uint64 escrowDeadline;
        State state;
        bytes32 deliveredHash;
    }

    struct Seal {
        bool sealed_;
        uint64 sealedAt;
        address formerOwner;
        bytes32 verifiedHash;
    }

    // -----------------------------------------------------------------
    // Storage
    // -----------------------------------------------------------------

    IERC20 public immutable paymentToken;
    IIdentityRegistry public immutable identityRegistry;

    /// @notice May confirm a transfer alongside the buyer. See the note above.
    address public immutable arbiter;

    /// @notice How long a buyer has to confirm before their escrow is reclaimable.
    uint64 public constant CONFIRMATION_WINDOW = 7 days;

    mapping(bytes32 listingId => Listing) private _listings;

    /// @notice Sealed agents, readable by the ACP registry or any future buyer.
    mapping(uint256 agentId => Seal) public seals;

    // -----------------------------------------------------------------
    // Events
    // -----------------------------------------------------------------

    event Listed(
        bytes32 indexed listingId,
        address indexed seller,
        uint256 indexed agentId,
        bytes32 hashCommitment,
        uint256 price
    );
    event Escrowed(bytes32 indexed listingId, address indexed buyer, uint256 amount);
    event TransferConfirmed(
        bytes32 indexed listingId,
        address indexed buyer,
        uint256 indexed agentId,
        bytes32 verifiedHash,
        uint256 amountReleased
    );
    event Refunded(bytes32 indexed listingId, address indexed buyer, uint256 amount, string reason);
    event AgentSealed(uint256 indexed agentId, address indexed formerOwner, bytes32 verifiedHash);

    // -----------------------------------------------------------------
    // Errors
    // -----------------------------------------------------------------

    error ListingExists();
    error NoSuchListing();
    error WrongState(State expected, State actual);
    error ZeroPrice();
    error ZeroCommitment();
    error SelfPurchase();
    error NotAuthorised();
    error RegistryNotApproved();
    error NotAgentOwner();
    error BadAttestation();
    error TransferFailed();
    error WindowNotElapsed();
    error AgentAlreadySealed();

    // -----------------------------------------------------------------

    constructor(IERC20 paymentToken_, IIdentityRegistry identityRegistry_, address arbiter_) {
        paymentToken = paymentToken_;
        identityRegistry = identityRegistry_;
        arbiter = arbiter_;
    }

    // -----------------------------------------------------------------
    // Listing
    // -----------------------------------------------------------------

    /// @notice Post a memory asset for sale.
    /// @param listingId       Caller-chosen identifier, unique per contract.
    /// @param agentId         The seller's ERC-8004 token id.
    /// @param hashCommitment  Merkle root over the SMP package being sold.
    /// @param price           Asking price, in `paymentToken` units.
    /// @param attestation     The seller's EIP-191 signature over
    ///                        `attestationDigest(listingId, agentId, hashCommitment)`.
    ///
    /// @dev Three preconditions are checked here rather than at settlement, so a
    ///      listing that cannot possibly settle never appears in the market: the
    ///      seller must own the agent, must have approved this contract to move
    ///      it, and must have signed an attestation that recovers to their own
    ///      address. Discovering any of these at `confirmTransfer` time would
    ///      mean a buyer's funds sat in escrow against a sale that was never
    ///      capable of completing.
    function list(
        bytes32 listingId,
        uint256 agentId,
        bytes32 hashCommitment,
        uint256 price,
        bytes calldata attestation
    ) external {
        if (_listings[listingId].state != State.None) revert ListingExists();
        if (price == 0) revert ZeroPrice();
        if (hashCommitment == bytes32(0)) revert ZeroCommitment();
        if (seals[agentId].sealed_) revert AgentAlreadySealed();

        if (identityRegistry.ownerOf(agentId) != msg.sender) revert NotAgentOwner();
        if (
            identityRegistry.getApproved(agentId) != address(this)
                && !identityRegistry.isApprovedForAll(msg.sender, address(this))
        ) revert RegistryNotApproved();

        if (_recover(attestationDigest(listingId, agentId, hashCommitment), attestation) != msg.sender) {
            revert BadAttestation();
        }

        _listings[listingId] = Listing({
            seller: msg.sender,
            buyer: address(0),
            agentId: agentId,
            hashCommitment: hashCommitment,
            price: price,
            escrowDeadline: 0,
            state: State.Open,
            deliveredHash: bytes32(0)
        });

        emit Listed(listingId, msg.sender, agentId, hashCommitment, price);
    }

    // -----------------------------------------------------------------
    // Escrow
    // -----------------------------------------------------------------

    /// @notice Fund escrow at exactly the asking price. Requires prior approval.
    function buy(bytes32 listingId) external {
        Listing storage listing = _get(listingId);
        if (listing.state != State.Open) revert WrongState(State.Open, listing.state);
        if (msg.sender == listing.seller) revert SelfPurchase();

        listing.buyer = msg.sender;
        listing.state = State.Escrowed;
        listing.escrowDeadline = uint64(block.timestamp) + CONFIRMATION_WINDOW;

        if (!paymentToken.transferFrom(msg.sender, address(this), listing.price)) {
            revert TransferFailed();
        }

        emit Escrowed(listingId, msg.sender, listing.price);
    }

    // -----------------------------------------------------------------
    // Settlement
    // -----------------------------------------------------------------

    /// @notice Release payment, move the identity, and seal the seller — or refund.
    /// @param deliveredHash The root the caller re-derived from the memory that
    ///                      actually landed in the buyer's store.
    ///
    /// @dev A mismatch refunds rather than reverting. Reverting would leave the
    ///      escrow funded and the buyer needing to remember to call something
    ///      else; the refund is the specified behaviour on a bad delivery, so it
    ///      is what a mismatch does.
    function confirmTransfer(bytes32 listingId, bytes32 deliveredHash) external {
        Listing storage listing = _get(listingId);
        if (listing.state != State.Escrowed) revert WrongState(State.Escrowed, listing.state);
        if (msg.sender != listing.buyer && msg.sender != arbiter) revert NotAuthorised();

        listing.deliveredHash = deliveredHash;

        if (deliveredHash != listing.hashCommitment) {
            _refund(listingId, listing, "Hash mismatch - delivered memory does not match the committed hash.");
            return;
        }

        // Effects before interactions: the listing is Confirmed and the agent is
        // sealed before any external call, so a hostile token or registry cannot
        // re-enter into a second settlement of the same listing.
        listing.state = State.Confirmed;

        address seller = listing.seller;
        address buyer = listing.buyer;
        uint256 agentId = listing.agentId;
        uint256 amount = listing.price;

        seals[agentId] = Seal({
            sealed_: true,
            sealedAt: uint64(block.timestamp),
            formerOwner: seller,
            verifiedHash: deliveredHash
        });
        emit AgentSealed(agentId, seller, deliveredHash);

        // Identity first, then money. If the registry reverts — approval pulled,
        // token moved out from under the listing — the whole transaction reverts
        // and the seller is not paid for an identity that did not move. The
        // reverse order would have to trust the registry call to succeed after
        // the funds were already gone.
        identityRegistry.transferFrom(seller, buyer, agentId);

        if (!paymentToken.transfer(seller, amount)) revert TransferFailed();

        emit TransferConfirmed(listingId, buyer, agentId, deliveredHash, amount);
    }

    /// @notice Cancel a funded escrow and return the buyer's money.
    /// @dev Either party may abandon a sale that has not settled.
    function refund(bytes32 listingId, string calldata reason) external {
        Listing storage listing = _get(listingId);
        if (listing.state != State.Escrowed) revert WrongState(State.Escrowed, listing.state);
        if (msg.sender != listing.buyer && msg.sender != listing.seller && msg.sender != arbiter) {
            revert NotAuthorised();
        }
        _refund(listingId, listing, reason);
    }

    /// @notice Reclaim escrow the buyer never confirmed. Callable by anyone.
    /// @dev Without this, a buyer who funds escrow and then disappears — or whose
    ///      import machinery dies mid-transfer — locks their own money in this
    ///      contract permanently. Permissionless because the funds can only ever
    ///      go back to the buyer, so there is nobody to protect them from.
    function reclaimExpired(bytes32 listingId) external {
        Listing storage listing = _get(listingId);
        if (listing.state != State.Escrowed) revert WrongState(State.Escrowed, listing.state);
        if (block.timestamp < listing.escrowDeadline) revert WindowNotElapsed();
        _refund(listingId, listing, "Confirmation window elapsed without a verified delivery.");
    }

    function _refund(bytes32 listingId, Listing storage listing, string memory reason) private {
        listing.state = State.Refunded;
        address buyer = listing.buyer;
        uint256 amount = listing.price;
        if (!paymentToken.transfer(buyer, amount)) revert TransferFailed();
        emit Refunded(listingId, buyer, amount, reason);
    }

    // -----------------------------------------------------------------
    // Views
    // -----------------------------------------------------------------

    function getListing(bytes32 listingId) external view returns (Listing memory) {
        return _get(listingId);
    }

    function isSealed(uint256 agentId) external view returns (bool) {
        return seals[agentId].sealed_;
    }

    /// @notice The message the seller attests to at listing time.
    /// @dev Binds the chain id and this contract's address as well as the sale
    ///      terms, so an attestation signed for one listing cannot be replayed
    ///      onto another listing, another deployment, or another chain.
    function attestationDigest(bytes32 listingId, uint256 agentId, bytes32 hashCommitment)
        public
        view
        returns (bytes32)
    {
        return keccak256(
            abi.encode(
                keccak256("Succession/1.0/listing-attestation"),
                block.chainid,
                address(this),
                listingId,
                agentId,
                hashCommitment
            )
        );
    }

    // -----------------------------------------------------------------
    // Internals
    // -----------------------------------------------------------------

    function _get(bytes32 listingId) private view returns (Listing storage listing) {
        listing = _listings[listingId];
        if (listing.state == State.None) revert NoSuchListing();
    }

    /// @dev EIP-191 personal-sign recovery, with the malleability guards.
    function _recover(bytes32 digest, bytes calldata signature) private pure returns (address) {
        if (signature.length != 65) return address(0);

        bytes32 r;
        bytes32 s;
        uint8 v;
        assembly {
            r := calldataload(signature.offset)
            s := calldataload(add(signature.offset, 32))
            v := byte(0, calldataload(add(signature.offset, 64)))
        }
        if (v < 27) v += 27;
        if (v != 27 && v != 28) return address(0);
        // Reject the high-s half of the curve: every signature has a second,
        // equally valid encoding, and accepting both means one attestation has
        // two distinct byte representations.
        if (uint256(s) > 0x7FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF5D576E7357A4501DDFE92F46681B20A0) {
            return address(0);
        }

        bytes32 prefixed = keccak256(abi.encodePacked("\x19Ethereum Signed Message:\n32", digest));
        return ecrecover(prefixed, v, r, s);
    }
}
