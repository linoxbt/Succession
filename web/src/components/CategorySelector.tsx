/**
 * The partial-succession step, between Listing and Escrow.
 *
 * A checklist of SMP categories. Per the brief, anything the seller marked
 * non-transferable is greyed out and genuinely unselectable — `disabled`, not
 * merely unchecked — because an unchecked box invites a buyer to tick it.
 */
import { useState } from "react";
import { Button, Notice, Rule, Section } from "./primitives";

const CATEGORIES: { id: string; label: string; description: string }[] = [
  { id: "identity", label: "Identity", description: "The agent's own registration record." },
  { id: "relationships", label: "Relationships", description: "Per-counterparty records and the edges between them." },
  { id: "preferences", label: "Preferences", description: "Learned settings and operating limits." },
  { id: "history", label: "History", description: "The time-ordered journal, and archived records." },
  { id: "commitments", label: "Commitments", description: "Open quotes, agreed terms, and live working state." },
  { id: "learned-behaviors", label: "Learned behaviors", description: "Adapted patterns and encoded playbooks." },
];

export function CategorySelector({
  onConfirm,
  busy,
  locked = [],
}: {
  onConfirm: (categories: string[] | null) => void;
  busy: boolean;
  locked?: string[];
}) {
  const [selected, setSelected] = useState<string[]>(CATEGORIES.map((c) => c.id));

  const selectable = CATEGORIES.filter((c) => !locked.includes(c.id));
  const all = selected.length === selectable.length;

  function toggle(id: string) {
    setSelected((current) =>
      current.includes(id) ? current.filter((c) => c !== id) : [...current, id],
    );
  }

  return (
    <div className="space-y-10">
      <header className="space-y-2">
        <p className="font-sans text-xs uppercase tracking-[0.16em] text-ink/50">
          Scope of transfer
        </p>
        <h1 className="font-serif text-4xl leading-tight">Select categories</h1>
        <p className="max-w-2xl font-sans text-[0.9375rem] leading-relaxed text-ink/70">
          A partial succession commits its own hash, computed over exactly what
          is being sold.
        </p>
      </header>

      <Section>
        <div className="border border-rule">
          {CATEGORIES.map((category, i) => {
            const isLocked = locked.includes(category.id);
            const checked = !isLocked && selected.includes(category.id);
            return (
              <div key={category.id}>
                {i > 0 ? <Rule /> : null}
                <label
                  className={`flex items-start gap-4 p-4 ${
                    isLocked ? "cursor-not-allowed opacity-45" : "cursor-pointer"
                  }`}
                >
                  <input
                    type="checkbox"
                    checked={checked}
                    disabled={isLocked || busy}
                    onChange={() => toggle(category.id)}
                    className="mt-1 h-4 w-4 accent-ink"
                  />
                  <span>
                    <span className="block font-sans text-sm font-medium">
                      {category.label}
                      {isLocked ? (
                        <span className="ml-2 font-normal text-ink/55">
                          — marked non-transferable
                        </span>
                      ) : null}
                    </span>
                    <span className="mt-0.5 block font-sans text-sm text-ink/55">
                      {category.description}
                    </span>
                  </span>
                </label>
              </div>
            );
          })}
        </div>
      </Section>

      {selected.length === 0 ? (
        <Notice tone="void">Select at least one category to transfer.</Notice>
      ) : null}

      <div className="flex flex-wrap gap-3 pt-2">
        <Button
          onClick={() => onConfirm(all ? null : selected)}
          disabled={busy || selected.length === 0}
        >
          {busy ? "Posting listing…" : all ? "List full succession" : `List ${selected.length} categories`}
        </Button>
        <Button tone="quiet" onClick={() => setSelected(selectable.map((c) => c.id))} disabled={busy}>
          Select all
        </Button>
      </div>
    </div>
  );
}
