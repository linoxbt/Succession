// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {Test} from "forge-std/Test.sol";
import {ListingContract} from "../src/ListingContract.sol";
import {IERC20} from "../src/interfaces/IERC20.sol";
import {IIdentityRegistry} from "../src/interfaces/IIdentityRegistry.sol";
import {MockERC20} from "./mocks/MockERC20.sol";
import {MockIdentityRegistry} from "./mocks/MockIdentityRegistry.sol";

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

    function _list() internal {
        vm.prank(seller);
        listings.list(LISTING_ID, AGENT_ID, COMMITMENT, PRICE, _attest(LISTING_ID, COMMITMENT, sellerKey));
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
        vm.prank(stranger);
        vm.expectRevert(ListingContract.NotAgentOwner.selector);
        listings.list(LISTING_ID, AGENT_ID, COMMITMENT, PRICE, _attest(LISTING_ID, COMMITMENT, sellerKey));
    }

    function test_listRequiresRegistryApproval() public {
        vm.prank(seller);
        registry.approve(address(0), AGENT_ID);
        vm.prank(seller);
        vm.expectRevert(ListingContract.RegistryNotApproved.selector);
        listings.list(LISTING_ID, AGENT_ID, COMMITMENT, PRICE, _attest(LISTING_ID, COMMITMENT, sellerKey));
    }

    function test_listRejectsAForeignAttestation() public {
        vm.prank(seller);
        vm.expectRevert(ListingContract.BadAttestation.selector);
        listings.list(LISTING_ID, AGENT_ID, COMMITMENT, PRICE, _attest(LISTING_ID, COMMITMENT, 0xBADBAD));
    }

    function test_anAttestationDoesNotReplayOntoAnotherListing() public {
        _list();
        bytes32 second = bytes32("listing-second");
        vm.prank(seller);
        vm.expectRevert(ListingContract.BadAttestation.selector);
        listings.list(second, AGENT_ID, COMMITMENT, PRICE, _attest(LISTING_ID, COMMITMENT, sellerKey));
    }

    function test_listRejectsAZeroCommitment() public {
        vm.prank(seller);
        vm.expectRevert(ListingContract.ZeroCommitment.selector);
        listings.list(LISTING_ID, AGENT_ID, bytes32(0), PRICE, _attest(LISTING_ID, bytes32(0), sellerKey));
    }

    function test_listRejectsADuplicateId() public {
        _list();
        vm.prank(seller);
        vm.expectRevert(ListingContract.ListingExists.selector);
        listings.list(LISTING_ID, AGENT_ID, COMMITMENT, PRICE, _attest(LISTING_ID, COMMITMENT, sellerKey));
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
        vm.prank(buyer);
        vm.expectRevert(ListingContract.AgentAlreadySealed.selector);
        listings.list(second, AGENT_ID, COMMITMENT, PRICE, _attest(second, COMMITMENT, sellerKey));
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
