// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {Test} from "forge-std/Test.sol";
import {ListingContract} from "../src/ListingContract.sol";
import {IERC20} from "../src/interfaces/IERC20.sol";
import {IIdentityRegistry} from "../src/interfaces/IIdentityRegistry.sol";
import {MockERC20} from "./mocks/MockERC20.sol";
import {MockIdentityRegistry} from "./mocks/MockIdentityRegistry.sol";
import {FeeOnTransferToken} from "./mocks/FeeOnTransferToken.sol";

/// @notice The Foundry suite. Mirrors packages/succession/tests/test_contract.py,
///         which executes the same compiled bytecode through py-evm where forge
///         is unavailable. Both must pass; they are the same scenarios.
contract ListingContractTest is Test {
    ListingContract internal listings;
    MockERC20 internal token;
    MockIdentityRegistry internal registry;

    uint256 internal constant AGENT_ID = 417;
    uint256 internal constant PRICE = 420_000_000;
    bytes32 internal constant COMMITMENT = bytes32(uint256(0x9f3a1c8ec21edb04));
    bytes32 internal constant WRONG = bytes32(uint256(0xdead));
    bytes32 internal constant LISTING_ID = bytes32("listing-0417");
    string internal constant AGENT_URI = "ipfs://meridian-logistics/registration.json";

    uint256 internal sellerKey = 0xA11CE;
    address internal seller;
    address internal buyer = address(0xB0B);
    address internal arbiter = address(0xA787);
    address internal stranger = address(0x5747);

    function setUp() public {
        seller = vm.addr(sellerKey);
        token = new MockERC20();
        registry = new MockIdentityRegistry();
        listings = new ListingContract(
            IERC20(address(token)), IIdentityRegistry(address(registry)), arbiter
        );

        registry.register(seller, AGENT_ID, AGENT_URI);
        vm.prank(seller);
        registry.approve(address(listings), AGENT_ID);

        token.mint(buyer, PRICE * 4);
        vm.prank(buyer);
        token.approve(address(listings), PRICE * 4);
    }

    function _attest(bytes32 listingId, bytes32 commitment, uint256 key)
        internal
        view
        returns (bytes memory)
    {
        bytes32 digest = listings.attestationDigest(listingId, AGENT_ID, commitment);
        bytes32 prefixed = keccak256(abi.encodePacked("\x19Ethereum Signed Message:\n32", digest));
        (uint8 v, bytes32 r, bytes32 s) = vm.sign(key, prefixed);
        return abi.encodePacked(r, s, v);
    }

    /// @dev Every attestation is built into a local *before* the cheatcode that
    ///      follows it. `_attest` calls `listings.attestationDigest`, and an
    ///      external call in an argument list is evaluated before the call it is
    ///      an argument to — so building it inline would spend the `vm.prank` on
    ///      the digest staticcall and leave `list` running as this test contract,
    ///      or bind the `vm.expectRevert` to the staticcall instead of `list`.
    function _list() internal {
        bytes memory attestation = _attest(LISTING_ID, COMMITMENT, sellerKey);
        vm.prank(seller);
        listings.list(LISTING_ID, AGENT_ID, COMMITMENT, PRICE, attestation);
    }

    function _escrow() internal {
        _list();
        vm.prank(buyer);
        listings.buy(LISTING_ID);
    }

    // -- listing ----------------------------------------------------------

    function test_listRecordsTheCommitment() public {
        _list();
        ListingContract.Listing memory listing = listings.getListing(LISTING_ID);
        assertEq(listing.seller, seller);
        assertEq(listing.agentId, AGENT_ID);
        assertEq(listing.hashCommitment, COMMITMENT);
        assertEq(listing.price, PRICE);
        assertEq(uint8(listing.state), uint8(ListingContract.State.Open));
    }

    function test_listRejectsANonOwner() public {
        bytes memory attestation = _attest(LISTING_ID, COMMITMENT, sellerKey);
        vm.prank(stranger);
        vm.expectRevert(ListingContract.NotAgentOwner.selector);
        listings.list(LISTING_ID, AGENT_ID, COMMITMENT, PRICE, attestation);
    }

    function test_listRequiresRegistryApproval() public {
        bytes memory attestation = _attest(LISTING_ID, COMMITMENT, sellerKey);
        vm.prank(seller);
        registry.approve(address(0), AGENT_ID);
        vm.prank(seller);
        vm.expectRevert(ListingContract.RegistryNotApproved.selector);
        listings.list(LISTING_ID, AGENT_ID, COMMITMENT, PRICE, attestation);
    }

    function test_listRejectsAForeignAttestation() public {
        bytes memory attestation = _attest(LISTING_ID, COMMITMENT, 0xBADBAD);
        vm.prank(seller);
        vm.expectRevert(ListingContract.BadAttestation.selector);
        listings.list(LISTING_ID, AGENT_ID, COMMITMENT, PRICE, attestation);
    }

    /// @dev The first listing is cancelled so the agent is free again; without
    ///      that, `AgentAlreadyListed` fires first and the attestation check —
    ///      the thing this test exists to cover — is never reached.
    function test_anAttestationDoesNotReplayOntoAnotherListing() public {
        _list();
        vm.prank(seller);
        listings.cancel(LISTING_ID);

        bytes32 second = bytes32("listing-second");
        bytes memory attestation = _attest(LISTING_ID, COMMITMENT, sellerKey);
        vm.prank(seller);
        vm.expectRevert(ListingContract.BadAttestation.selector);
        listings.list(second, AGENT_ID, COMMITMENT, PRICE, attestation);
    }

    function test_listRejectsAZeroCommitment() public {
        bytes memory attestation = _attest(LISTING_ID, bytes32(0), sellerKey);
        vm.prank(seller);
        vm.expectRevert(ListingContract.ZeroCommitment.selector);
        listings.list(LISTING_ID, AGENT_ID, bytes32(0), PRICE, attestation);
    }

    function test_listRejectsADuplicateId() public {
        _list();
        bytes memory attestation = _attest(LISTING_ID, COMMITMENT, sellerKey);
        vm.prank(seller);
        vm.expectRevert(ListingContract.ListingExists.selector);
        listings.list(LISTING_ID, AGENT_ID, COMMITMENT, PRICE, attestation);
    }

    function test_anAgentCannotBeListedTwiceAtOnce() public {
        _list();
        bytes32 second = bytes32("listing-second");
        bytes memory attestation = _attest(second, COMMITMENT, sellerKey);
        vm.prank(seller);
        vm.expectRevert(
            abi.encodeWithSelector(ListingContract.AgentAlreadyListed.selector, LISTING_ID)
        );
        listings.list(second, AGENT_ID, COMMITMENT, PRICE, attestation);
    }

    function test_theSellerCanCancelAnUnfundedListing() public {
        _list();
        vm.prank(seller);
        listings.cancel(LISTING_ID);
        assertEq(
            uint8(listings.getListing(LISTING_ID).state), uint8(ListingContract.State.Refunded)
        );
        assertEq(listings.activeListing(AGENT_ID), bytes32(0));
    }

    function test_cancellingFreesTheAgentToBeRelisted() public {
        _list();
        vm.prank(seller);
        listings.cancel(LISTING_ID);

        bytes32 second = bytes32("listing-second");
        bytes memory attestation = _attest(second, COMMITMENT, sellerKey);
        vm.prank(seller);
        listings.list(second, AGENT_ID, COMMITMENT, PRICE, attestation);
        assertEq(listings.activeListing(AGENT_ID), second);
    }

    function test_onlyTheSellerMayCancel() public {
        _list();
        vm.prank(stranger);
        vm.expectRevert(ListingContract.NotAuthorised.selector);
        listings.cancel(LISTING_ID);
    }

    function test_aFundedListingCannotBeCancelled() public {
        _escrow();
        vm.prank(seller);
        vm.expectRevert(
            abi.encodeWithSelector(
                ListingContract.WrongState.selector,
                ListingContract.State.Open,
                ListingContract.State.Escrowed
            )
        );
        listings.cancel(LISTING_ID);
    }

    function test_aRefundFreesTheAgentToBeRelisted() public {
        _escrow();
        vm.prank(seller);
        listings.refund(LISTING_ID, "seller withdrew");
        assertEq(listings.activeListing(AGENT_ID), bytes32(0));

        bytes32 second = bytes32("listing-second");
        bytes memory attestation = _attest(second, COMMITMENT, sellerKey);
        vm.prank(seller);
        listings.list(second, AGENT_ID, COMMITMENT, PRICE, attestation);
        assertEq(listings.activeListing(AGENT_ID), second);
    }

    // -- escrow -----------------------------------------------------------

    function test_buyEscrowsTheFunds() public {
        _list();
        uint256 before = token.balanceOf(buyer);
        vm.prank(buyer);
        listings.buy(LISTING_ID);
        assertEq(token.balanceOf(buyer), before - PRICE);
        assertEq(token.balanceOf(address(listings)), PRICE);
    }

    function test_sellerCannotBuyTheirOwnListing() public {
        _list();
        token.mint(seller, PRICE);
        vm.prank(seller);
        token.approve(address(listings), PRICE);
        vm.prank(seller);
        vm.expectRevert(ListingContract.SelfPurchase.selector);
        listings.buy(LISTING_ID);
    }

    function test_aFeeTakingTokenIsRejectedRatherThanShortingTheSeller() public {
        FeeOnTransferToken fee = new FeeOnTransferToken();
        MockIdentityRegistry reg = new MockIdentityRegistry();
        ListingContract lc = new ListingContract(
            IERC20(address(fee)), IIdentityRegistry(address(reg)), arbiter
        );
        reg.register(seller, AGENT_ID, AGENT_URI);
        vm.prank(seller);
        reg.approve(address(lc), AGENT_ID);
        fee.mint(buyer, PRICE * 2);
        vm.prank(buyer);
        fee.approve(address(lc), PRICE * 2);

        bytes32 digest = lc.attestationDigest(LISTING_ID, AGENT_ID, COMMITMENT);
        bytes32 prefixed =
            keccak256(abi.encodePacked("\x19Ethereum Signed Message:\n32", digest));
        (uint8 v, bytes32 r, bytes32 s) = vm.sign(sellerKey, prefixed);
        vm.prank(seller);
        lc.list(LISTING_ID, AGENT_ID, COMMITMENT, PRICE, abi.encodePacked(r, s, v));

        vm.prank(buyer);
        vm.expectRevert(
            abi.encodeWithSelector(
                ListingContract.EscrowShortfall.selector, PRICE, PRICE - (PRICE / 100)
            )
        );
        lc.buy(LISTING_ID);
    }

    function test_oneListingIsNeverSettledOutOfAnothersEscrow() public {
        // A second agent, a second buyer, a second escrow — settling the first
        // must leave the second's money untouched.
        uint256 otherAgent = 999;
        address otherBuyer = address(0xB0B2);
        registry.register(seller, otherAgent, AGENT_URI);
        vm.prank(seller);
        registry.approve(address(listings), otherAgent);
        token.mint(otherBuyer, PRICE);
        vm.prank(otherBuyer);
        token.approve(address(listings), PRICE);

        _escrow();

        bytes32 second = bytes32("listing-other");
        bytes32 digest = listings.attestationDigest(second, otherAgent, COMMITMENT);
        bytes32 prefixed =
            keccak256(abi.encodePacked("\x19Ethereum Signed Message:\n32", digest));
        (uint8 v, bytes32 r, bytes32 s) = vm.sign(sellerKey, prefixed);
        vm.prank(seller);
        listings.list(second, otherAgent, COMMITMENT, PRICE, abi.encodePacked(r, s, v));
        vm.prank(otherBuyer);
        listings.buy(second);

        assertEq(token.balanceOf(address(listings)), PRICE * 2);

        vm.prank(buyer);
        listings.confirmTransfer(LISTING_ID, COMMITMENT);

        // The other listing's escrow is still whole and still refundable.
        assertEq(token.balanceOf(address(listings)), PRICE);
        uint256 before = token.balanceOf(otherBuyer);
        vm.prank(otherBuyer);
        listings.refund(second, "changed my mind");
        assertEq(token.balanceOf(otherBuyer), before + PRICE);
        assertEq(token.balanceOf(address(listings)), 0);
    }

    // -- settlement -------------------------------------------------------

    function test_confirmPaysMovesAndSealsAtomically() public {
        _escrow();
        uint256 sellerBefore = token.balanceOf(seller);

        vm.prank(buyer);
        listings.confirmTransfer(LISTING_ID, COMMITMENT);

        assertEq(token.balanceOf(seller), sellerBefore + PRICE);
        assertEq(registry.ownerOf(AGENT_ID), buyer);
        assertTrue(listings.isSealed(AGENT_ID));
        assertEq(token.balanceOf(address(listings)), 0);
    }

    function test_aMismatchRefundsAndChangesNothingElse() public {
        _escrow();
        uint256 buyerBefore = token.balanceOf(buyer);

        vm.prank(buyer);
        listings.confirmTransfer(LISTING_ID, WRONG);

        assertEq(token.balanceOf(buyer), buyerBefore + PRICE);
        assertEq(registry.ownerOf(AGENT_ID), seller);
        assertFalse(listings.isSealed(AGENT_ID));
    }

    function test_onlyTheBuyerOrArbiterMayConfirm() public {
        _escrow();
        vm.prank(stranger);
        vm.expectRevert(ListingContract.NotAuthorised.selector);
        listings.confirmTransfer(LISTING_ID, COMMITMENT);

        vm.prank(seller);
        vm.expectRevert(ListingContract.NotAuthorised.selector);
        listings.confirmTransfer(LISTING_ID, COMMITMENT);
    }

    function test_theArbiterCanConfirm() public {
        _escrow();
        vm.prank(arbiter);
        listings.confirmTransfer(LISTING_ID, COMMITMENT);
        assertEq(registry.ownerOf(AGENT_ID), buyer);
    }

    function test_settlementCannotHappenTwice() public {
        _escrow();
        vm.prank(buyer);
        listings.confirmTransfer(LISTING_ID, COMMITMENT);

        vm.prank(buyer);
        vm.expectRevert(
            abi.encodeWithSelector(
                ListingContract.WrongState.selector,
                ListingContract.State.Escrowed,
                ListingContract.State.Confirmed
            )
        );
        listings.confirmTransfer(LISTING_ID, COMMITMENT);
    }

    function test_aSealedAgentCannotBeRelisted() public {
        _escrow();
        vm.prank(buyer);
        listings.confirmTransfer(LISTING_ID, COMMITMENT);

        vm.prank(buyer);
        registry.approve(address(listings), AGENT_ID);
        bytes32 second = bytes32("listing-second");
        bytes memory attestation = _attest(second, COMMITMENT, sellerKey);
        vm.prank(buyer);
        vm.expectRevert(ListingContract.AgentAlreadySealed.selector);
        listings.list(second, AGENT_ID, COMMITMENT, PRICE, attestation);
    }

    // -- refunds ----------------------------------------------------------

    function test_eitherPartyMayAbandonAFundedSale() public {
        _escrow();
        uint256 before = token.balanceOf(buyer);
        vm.prank(seller);
        listings.refund(LISTING_ID, "seller withdrew");
        assertEq(token.balanceOf(buyer), before + PRICE);
    }

    function test_aStrangerCannotRefund() public {
        _escrow();
        vm.prank(stranger);
        vm.expectRevert(ListingContract.NotAuthorised.selector);
        listings.refund(LISTING_ID, "mine now");
    }

    function test_escrowIsNotReclaimableBeforeTheWindow() public {
        _escrow();
        vm.expectRevert(ListingContract.WindowNotElapsed.selector);
        listings.reclaimExpired(LISTING_ID);
    }

    function test_abandonedEscrowIsReclaimableByAnyone() public {
        _escrow();
        uint256 before = token.balanceOf(buyer);
        vm.warp(block.timestamp + 8 days);

        vm.prank(stranger);
        listings.reclaimExpired(LISTING_ID);

        assertEq(token.balanceOf(buyer), before + PRICE);
        assertEq(registry.ownerOf(AGENT_ID), seller);
        assertFalse(listings.isSealed(AGENT_ID));
    }

    // -- fuzz -------------------------------------------------------------

    /// @dev Any hash that is not the commitment must refund, never release.
    function testFuzz_onlyTheCommittedHashReleases(bytes32 delivered) public {
        vm.assume(delivered != COMMITMENT);
        _escrow();
        uint256 buyerBefore = token.balanceOf(buyer);

        vm.prank(buyer);
        listings.confirmTransfer(LISTING_ID, delivered);

        assertEq(token.balanceOf(buyer), buyerBefore + PRICE);
        assertEq(registry.ownerOf(AGENT_ID), seller);
        assertFalse(listings.isSealed(AGENT_ID));
    }
}
