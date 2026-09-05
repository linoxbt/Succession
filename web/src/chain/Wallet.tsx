/**
 * The wallet strip, and the escrow controls that spend from it.
 *
 * Two things this file is careful about.
 *
 * **It never claims a chain it is not on.** `SettlementMode` renders what the
 * service reports, local mirror or deployed contract, in the same words the
 * service uses. `LocalSettlement` mirrors the contract's state machine closely
 * enough that a screen showing only the outcome could not tell them apart, so
 * the screen says which one produced it.
 *
 * **It surfaces the contract's own refusal.** ListingContract reverts with
 * named custom errors, `WrongState`, `NotAuthorised`, `SelfPurchase`. The
 * generated ABI carries them, so a failure reads as the sentence the contract
 * meant rather than as a hex selector.
 */
import { useCallback, useEffect, useRef, useState } from "react";
import {
  useAccount,
  useChainId,
  useConnect,
  useDisconnect,
  useReadContract,
  useSwitchChain,
  useWaitForTransactionReceipt,
  useWriteContract,
} from "wagmi";
import { Badge, Button, Field, FieldList, Hash, Note } from "../ui";
import { ERC20_ABI, LISTING_ABI } from "./abi";
import { CHAIN, explorerAddress, explorerTx } from "./config";

export interface Deployment {
  listing_contract: string;
  identity_registry: string;
  identity_registry_is_mock: boolean;
  payment_token: string;
  arbiter: string;
  chain_id: number;
  explorer?: string;
}

export interface ChainStatus {
  // "none" when no deployment record exists. There is deliberately no third
  // state: a flag that turned on chain mode without a deployment would be a
  // flag that could be set wrongly.
  mode: "none" | "chain";
  explanation: string;
  chain_id: number | null;
  deployment: Deployment | null;
}

/**
 * Encode a listing id the way Python's `listing_id_to_bytes32` does: UTF-8,
 * right-padded to 32 bytes.
 *
 * Re-implemented here rather than fetched because the browser builds its own
 * calldata. The failure mode if these two drift is nastier than a type error:
 * a mismatched key does not fault, it addresses a *different* storage slot, so
 * the contract reports `NoSuchListing` for a listing that plainly exists.
 * `test_listing_id_encoding_vectors` pins the shared vectors:
 *
 *   "listing-0417" -> 0x6c697374696e672d30343137...00
 *   "a"            -> 0x6100...00
 */
export function listingIdToBytes32(listingId: string): `0x${string}` {
  const bytes = new TextEncoder().encode(listingId);
  if (bytes.length > 32) throw new Error(`listing id too long: ${listingId}`);
  const padded = new Uint8Array(32);
  padded.set(bytes);
  return `0x${Array.from(padded, (b) => b.toString(16).padStart(2, "0")).join("")}`;
}

export function useChainStatus(): ChainStatus | null {
  const [status, setStatus] = useState<ChainStatus | null>(null);
  useEffect(() => {
    let live = true;
    fetch("/api/chain")
      .then((r) => (r.ok ? r.json() : null))
      .then((s) => live && setStatus(s))
      .catch(() => live && setStatus(null));
    return () => {
      live = false;
    };
  }, []);
  return status;
}

/* -- connection --------------------------------------------------------- */

export function WalletBar({ status }: { status: ChainStatus | null }) {
  const { address, isConnected } = useAccount();
  const { disconnect } = useDisconnect();
  const chainId = useChainId();
  const { switchChain } = useSwitchChain();

  if (!status || status.mode !== "chain") return null;

  const wrongChain = isConnected && chainId !== CHAIN.id;

  return (
    <div className="border-b border-rule">
      <div className="mx-auto flex max-w-wide flex-wrap items-center gap-x-5 gap-y-2 px-6 py-2.5">
        <span className="text-micro text-muted">
          Settling on {CHAIN.name}
        </span>

        {isConnected ? (
          <>
            <Hash value={address ?? ""} chars={6} />
            {wrongChain ? (
              <>
                <Badge tone="void">Wrong network</Badge>
                <button
                  onClick={() => switchChain({ chainId: CHAIN.id })}
                  className="text-micro underline underline-offset-4 hover:text-escrow"
                >
                  Switch to {CHAIN.name}
                </button>
              </>
            ) : (
              <Badge tone="closed">Connected</Badge>
            )}
            <button
              onClick={() => disconnect()}
              className="text-micro text-muted underline underline-offset-4 hover:text-ink"
            >
              Disconnect
            </button>
          </>
        ) : (
          <ConnectButton />
        )}
      </div>
    </div>
  );
}

/**
 * The connect control.
 *
 * One button rather than a row of connector names. A visitor who has not
 * connected does not yet know which of Base Account, an injected wallet or
 * Reown they want, and presenting three equal links asks them to choose before
 * they have any reason to care. The button opens the choice; the choice is a
 * short list because there are only ever a few.
 *
 * Reown appears only when a project id was built in, so the list never offers a
 * route that would fail at the relay with an error nobody can act on.
 */
function ConnectButton() {
  const { connect, connectors, isPending, error } = useConnect();
  const [open, setOpen] = useState(false);
  const wrap = useRef<HTMLDivElement | null>(null);

  // Click-away, so the list does not strand itself open over the page.
  useEffect(() => {
    if (!open) return;
    const onDown = (e: PointerEvent) => {
      if (wrap.current && !wrap.current.contains(e.target as Node)) setOpen(false);
    };
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && setOpen(false);
    document.addEventListener("pointerdown", onDown);
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("pointerdown", onDown);
      document.removeEventListener("keydown", onKey);
    };
  }, [open]);

  return (
    <div ref={wrap} className="relative">
      <Button size="sm" onClick={() => setOpen((v) => !v)} disabled={isPending}>
        {isPending ? "Connecting…" : "Connect wallet"}
      </Button>

      {open ? (
        <div className="absolute right-0 top-full z-50 mt-2 min-w-[13rem] border border-rule bg-paper">
          {connectors.map((c) => (
            <button
              key={c.uid}
              onClick={() => {
                setOpen(false);
                connect({ connector: c });
              }}
              className="block w-full border-b border-hairline px-5 py-3 text-left text-micro text-ink transition-colors duration-400 last:border-b-0 hover:bg-shade"
            >
              {c.name}
            </button>
          ))}
        </div>
      ) : null}

      {error ? (
        <span className="ml-4 text-micro text-void">{error.message}</span>
      ) : null}
    </div>
  );
}

/* -- provenance of the settlement backend -------------------------------- */

/**
 * Says plainly which backend is settling. Rendered on the listing screen, not
 * tucked into a footer, a reader deciding whether to believe the hash
 * comparison needs to know this before they read it, not after.
 */
export function SettlementMode({ status }: { status: ChainStatus | null }) {
  if (!status) return null;
  const chain = status.mode === "chain";
  const d = status.deployment;

  return (
    <div className="mt-8">
      <div className="flex flex-wrap items-center gap-3 border-b border-rule pb-2">
        <h3 className="font-display text-heading text-ink">Settlement</h3>
        <Badge tone={chain ? "escrow" : "neutral"}>
          {chain ? `On chain, ${CHAIN.name}` : "Local mirror, not on chain"}
        </Badge>
      </div>
      <p className="mt-3 max-w-wide text-body leading-relaxed text-muted">
        {status.explanation}
      </p>
      {d ? (
        <FieldList className="mt-4">
          <Field label="Listing contract">
            <a
              className="underline underline-offset-4 hover:text-escrow"
              href={explorerAddress(d.listing_contract)}
              target="_blank"
              rel="noreferrer"
            >
              <Hash value={d.listing_contract} chars={8} />
            </a>
          </Field>
          <Field label="Payment token">
            <a
              className="underline underline-offset-4 hover:text-escrow"
              href={explorerAddress(d.payment_token)}
              target="_blank"
              rel="noreferrer"
            >
              <Hash value={d.payment_token} chars={8} />
            </a>
          </Field>
          <Field label="Identity registry">
            <span className="flex flex-wrap items-center gap-2">
              <a
                className="underline underline-offset-4 hover:text-escrow"
                href={explorerAddress(d.identity_registry)}
                target="_blank"
                rel="noreferrer"
              >
                <Hash value={d.identity_registry} chars={8} />
              </a>
              {d.identity_registry_is_mock ? (
                <Badge tone="void">Stand-in, not a real ERC-8004 registry</Badge>
              ) : (
                <Badge tone="closed">ERC-8004</Badge>
              )}
            </span>
          </Field>
          <Field label="Arbiter">
            <Hash value={d.arbiter} chars={8} />
            <span className="text-muted">, may confirm alongside the buyer</span>
          </Field>
        </FieldList>
      ) : null}
    </div>
  );
}

/* -- funding escrow from the buyer's own wallet -------------------------- */

/**
 * Approve, then `buy`. Two transactions, shown as two steps, because that is
 * what they are, collapsing them into one button that silently sends two
 * signature requests is how a user ends up approving a token spend they did not
 * read.
 */
export function FundEscrow({
  deployment,
  listingId,
  price,
  onFunded,
}: {
  deployment: Deployment;
  listingId: string;
  price: bigint;
  onFunded: (txHash: string) => void;
}) {
  const { address, isConnected } = useAccount();
  const chainId = useChainId();
  const listingKey = listingIdToBytes32(listingId);

  const { data: allowance, refetch: refetchAllowance } = useReadContract({
    address: deployment.payment_token as `0x${string}`,
    abi: ERC20_ABI,
    functionName: "allowance",
    args: address
      ? [address, deployment.listing_contract as `0x${string}`]
      : undefined,
    query: { enabled: Boolean(address) },
  });

  const { data: balance } = useReadContract({
    address: deployment.payment_token as `0x${string}`,
    abi: ERC20_ABI,
    functionName: "balanceOf",
    args: address ? [address] : undefined,
    query: { enabled: Boolean(address) },
  });

  const { writeContract, data: txHash, isPending, error, reset } = useWriteContract();
  const { isLoading: mining, isSuccess } = useWaitForTransactionReceipt({ hash: txHash });
  const [stage, setStage] = useState<"approve" | "buy">("approve");

  const approved = (allowance ?? 0n) >= price;
  const funded = (balance ?? 0n) >= price;

  // Which transaction hash has already been acted on. `isSuccess` and `txHash`
  // stay set after a receipt lands, so without this the effect re-runs on any
  // dependency change, including a parent re-render, and calls `onFunded`
  // again for a transaction that was already handled.
  const handled = useRef<string | null>(null);

  useEffect(() => {
    if (!isSuccess || !txHash) return;
    if (handled.current === txHash) return;
    handled.current = txHash;
    if (stage === "approve") {
      // Await the refetch before leaving the approve stage. Firing it and
      // moving on leaves `allowance` stale for a beat, during which the button
      // still reads "Approve the payment token" against a granted allowance,
      // and a user who takes it at its word signs a second, pointless approval.
      void refetchAllowance().finally(() => {
        setStage("buy");
        reset();
      });
    } else {
      onFunded(txHash);
    }
  }, [isSuccess, txHash, stage, refetchAllowance, reset, onFunded]);

  const approve = useCallback(() => {
    setStage("approve");
    writeContract({
      address: deployment.payment_token as `0x${string}`,
      abi: ERC20_ABI,
      functionName: "approve",
      args: [deployment.listing_contract as `0x${string}`, price],
    });
  }, [writeContract, deployment, price]);

  const buy = useCallback(() => {
    setStage("buy");
    writeContract({
      address: deployment.listing_contract as `0x${string}`,
      abi: LISTING_ABI,
      functionName: "buy",
      args: [listingKey],
    });
  }, [writeContract, deployment, listingKey]);

  if (!isConnected) {
    return <Note>Connect a wallet to fund escrow from your own address.</Note>;
  }
  if (chainId !== CHAIN.id) {
    return <Note>Switch to {CHAIN.name} to fund this escrow.</Note>;
  }
  if (!funded) {
    return (
      <Note>
        This wallet holds less than the asking price in the payment token. Base
        Sepolia USDC is available from the Circle faucet.
      </Note>
    );
  }

  const busy = isPending || mining;

  return (
    <div className="flex flex-col gap-3">
      <div className="flex flex-wrap items-center gap-4">
        <Button onClick={approved ? buy : approve} disabled={busy}>
          {busy
            ? "Waiting for the network…"
            : approved
              ? "Fund escrow"
              : "Approve the payment token"}
        </Button>
        <Note>
          {approved
            ? "The contract will pull exactly the asking price into escrow."
            : "Step 1 of 2, approve, then fund. Two transactions, shown as two."}
        </Note>
      </div>
      {txHash ? (
        <a
          className="text-micro underline underline-offset-4 hover:text-escrow"
          href={explorerTx(txHash)}
          target="_blank"
          rel="noreferrer"
        >
          View transaction on Basescan
        </a>
      ) : null}
      {error ? <ContractError error={error} /> : null}
    </div>
  );
}

/**
 * Submit the re-derived root. The buyer's own assertion, which is exactly the
 * hole the Evaluator exists to close, so the caller is expected to say so.
 */
export function ConfirmOnChain({
  deployment,
  listingId,
  deliveredRoot,
  onConfirmed,
}: {
  deployment: Deployment;
  listingId: string;
  deliveredRoot: string;
  onConfirmed: (txHash: string) => void;
}) {
  const { writeContract, data: txHash, isPending, error } = useWriteContract();
  const { isLoading: mining, isSuccess } = useWaitForTransactionReceipt({ hash: txHash });

  // See FundEscrow: the receipt state is sticky, so the effect must remember
  // which hash it has already reported rather than firing on every re-render.
  const handled = useRef<string | null>(null);

  useEffect(() => {
    if (!isSuccess || !txHash) return;
    if (handled.current === txHash) return;
    handled.current = txHash;
    onConfirmed(txHash);
  }, [isSuccess, txHash, onConfirmed]);

  return (
    <div className="flex flex-col gap-3">
      <div className="flex flex-wrap items-center gap-4">
        <Button
          disabled={isPending || mining}
          onClick={() =>
            writeContract({
              address: deployment.listing_contract as `0x${string}`,
              abi: LISTING_ABI,
              functionName: "confirmTransfer",
              args: [listingIdToBytes32(listingId), deliveredRoot as `0x${string}`],
            })
          }
        >
          {isPending || mining ? "Waiting for the network…" : "Confirm delivery on chain"}
        </Button>
        <Note>
          Payment, identity and the seal move in this one transaction, or none
          of them do.
        </Note>
      </div>
      {txHash ? (
        <a
          className="text-micro underline underline-offset-4 hover:text-escrow"
          href={explorerTx(txHash)}
          target="_blank"
          rel="noreferrer"
        >
          View transaction on Basescan
        </a>
      ) : null}
      {error ? <ContractError error={error} /> : null}
    </div>
  );
}

/**
 * A contract revert, in the contract's own vocabulary.
 *
 * wagmi surfaces the decoded custom error name when the ABI carries it, which
 * is why `generate-abi.mjs` keeps every `error` entry. A user who sees
 * `WrongState` can at least search for it; one who sees `0x1f2a3b4c` cannot.
 */
function ContractError({ error }: { error: Error }) {
  const message = extractRevert(error);
  return (
    <p className="max-w-wide text-micro leading-relaxed text-void">
      {message}
    </p>
  );
}

function extractRevert(error: Error): string {
  const text = error.message ?? String(error);
  // viem puts the decoded custom error on its own line; the rest is a stack.
  const named = text.match(/reverted with the following reason:\s*\n(.+)/);
  if (named?.[1]) return named[1].trim();
  const custom = text.match(/Error:\s*([A-Za-z_][A-Za-z0-9_]*)\(/);
  if (custom?.[1]) return `The contract refused this call: ${custom[1]}.`;
  if (/User rejected|denied transaction/i.test(text)) {
    return "Transaction rejected in the wallet. Nothing was sent.";
  }
  return text.split("\n")[0] ?? "The transaction failed.";
}
