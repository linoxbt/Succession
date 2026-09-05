/**
 * Choosing which of your agents inherits the memory.
 *
 * A buyer usually holds more than one ERC-8004 identity, and a sale lands in
 * exactly one of them: the memory is imported under that agent and the identity
 * token moves to the buyer at settlement. Guessing which would be picking the
 * successor on someone's behalf, so the console asks.
 *
 * The list is reconstructed from `Transfer` logs, because the registry is not
 * `ERC721Enumerable` and there is no `tokenOfOwnerByIndex` to call. That has a
 * consequence this component is careful about: the scan is bounded, so it can
 * miss an agent minted before the window. Every candidate is confirmed against
 * `ownerOf` and the total is reconciled against `balanceOf`, so the list is
 * never *wrong*, only sometimes short. When it is short the component says so
 * rather than presenting a partial list as the whole picture, because "you hold
 * no agents" and "we found three of your five" are different statements and a
 * buyer would act differently on each.
 */
import { useEffect, useState } from "react";
import { useAccount } from "wagmi";

import { market, type AgentsHeld } from "../api";
import { Note } from "../ui";

export default function AgentPicker({
  selected,
  onSelect,
}: {
  selected: string;
  onSelect: (identity: string) => void;
}) {
  const { address, isConnected } = useAccount();
  const [held, setHeld] = useState<AgentsHeld | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!address) {
      setHeld(null);
      return;
    }
    let live = true;
    setLoading(true);
    market
      .agents(address)
      .then((body) => {
        if (!live) return;
        setHeld(body);
        setError(null);
        // Pre-select when there is no choice to make.
        if (body.agents.length === 1 && body.agents[0]) {
          onSelect(body.agents[0].identity);
        }
      })
      .catch((e) => live && setError(e instanceof Error ? e.message : String(e)))
      .finally(() => live && setLoading(false));
    return () => {
      live = false;
    };
    // `onSelect` is intentionally omitted: it changes identity on every parent
    // render, and re-running this effect would re-fetch the registry each time.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [address]);

  if (!isConnected) {
    return <Note>Connect a wallet to choose which of your agents inherits this memory.</Note>;
  }
  if (loading) {
    return <Note>Reading your agents from the registry…</Note>;
  }
  if (error) {
    return <Note>Could not read the registry ({error}).</Note>;
  }
  if (!held || held.agents.length === 0) {
    return (
      <Note>
        No ERC-8004 agents found for this wallet. Register one before buying, so
        the memory has a successor to land in.
      </Note>
    );
  }

  return (
    <div>
      <div className="border-t border-hairline">
        {held.agents.map((agent) => {
          const active = selected === agent.identity;
          return (
            <button
              key={agent.identity}
              onClick={() => onSelect(agent.identity)}
              aria-pressed={active}
              className={`flex w-full items-baseline gap-6 border-b border-hairline py-5 text-left transition-[border-color,transform] duration-500 ease-swift ${
                active ? "border-l-2 border-l-ink pl-5" : "pl-0 hover:translate-x-1"
              }`}
            >
              <span
                className={`w-8 shrink-0 text-micro tnum ${active ? "text-ink" : "text-faint"}`}
              >
                {active ? "✓" : ""}
              </span>
              <span className={`evidence-type text-body ${active ? "text-ink" : "text-muted"}`}>
                {agent.identity}
              </span>
            </button>
          );
        })}
      </div>

      {!held.complete ? (
        <Note>
          Showing {held.found} of the {held.balance} agents this wallet holds. The
          registry cannot be enumerated directly, so older agents may sit outside
          the scanned range. Everything listed is confirmed on chain; the list is
          short rather than wrong.
        </Note>
      ) : null}
    </div>
  );
}
