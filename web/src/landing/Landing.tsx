/**
 * The landing document.
 *
 * Read top to bottom as one continuous composition rather than a stack of
 * panels: chapters are numbered, the ground alternates between paper and
 * carbon at full bleed, and elements from one chapter lead into the next. The
 * page is set edge-to-edge, the gutter is a margin, not a centring container,
 * so the type has room to run at the scale it is designed for.
 *
 * The product's own copy is unchanged. What changed is everything around it.
 */
import { useEffect, useRef, useState, type ReactNode } from "react";

import {
  MaskLine,
  Reveal,
  useCountUp,
  useCursorState,
  useParallax,
  useScrollScene,
  useScrollTo,
} from "../motion";
import { HashVerification, TransferDiagram } from "./visuals";
import { HashPlate, Lineage, MemoryField } from "./imagery";
import { Button, Figure } from "../ui";
import { Wordmark } from "../brand/Logo";
import { WalletBar } from "../chain/Wallet";

export function Landing({ onEnter, onDocs }: { onEnter: () => void; onDocs: () => void }) {
  return (
    <div className="bg-paper">
      <Masthead onEnter={onEnter} onDocs={onDocs} />
      <Hero onEnter={onEnter} onDocs={onDocs} />
      <Thesis />
      <Plate caption="Accumulation" tone="carbon">
        <MemoryField className="h-full w-full" />
      </Plate>
      <Mechanism />
      <Plate caption="Inheritance">
        <Lineage className="h-full w-full" />
      </Plate>
      <Verification />
      <Commitment />
      <Proof />
      <Stacks />
      <Plate caption="Evidence" height="h-[46vh] sm:h-[58vh]">
        <HashPlate className="h-full w-full" />
      </Plate>
      <Lifecycle />
      <Close onEnter={onEnter} />
      <Colophon onDocs={onDocs} />
    </div>
  );
}

/* -- masthead ------------------------------------------------------------ */

function Masthead({ onEnter, onDocs }: { onEnter: () => void; onDocs: () => void }) {
  const [solid, setSolid] = useState(false);
  const [open, setOpen] = useState(false);
  useEffect(() => {
    const onScroll = () => setSolid(window.scrollY > 40);
    onScroll();
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  return (
    <>
      <LandingMenu
        open={open}
        onClose={() => setOpen(false)}
        onEnter={onEnter}
        onDocs={onDocs}
      />
    <header
      className={`fixed inset-x-0 top-0 z-50 transition-all duration-700 ease-swift ${
        solid ? "border-b border-rule bg-paper/95 py-3" : "border-b border-transparent py-6"
      }`}
    >
      <div className="gutter flex items-center justify-between gap-6">
        <Wordmark size={solid ? 24 : 30} />
        <div className="flex items-center gap-6 sm:gap-8">
          <WalletBar />
          <button
            onClick={() => setOpen((v) => !v)}
            className="link-underline font-mono text-label uppercase text-ink"
            aria-expanded={open}
            aria-controls="landing-menu"
          >
            {open ? "Close" : "Menu"}
          </button>
        </div>
      </div>
    </header>
    </>
  );
}

/**
 * The landing menu.
 *
 * Same button and same overlay as the console, so the two halves of the product
 * open in one gesture rather than each inventing its own. Destinations are set
 * at display scale because a menu that has the whole viewport should use it.
 */
function LandingMenu({
  open,
  onClose,
  onEnter,
  onDocs,
}: {
  open: boolean;
  onClose: () => void;
  onEnter: () => void;
  onDocs: () => void;
}) {
  useEffect(() => {
    document.body.style.overflow = open ? "hidden" : "";
    return () => {
      document.body.style.overflow = "";
    };
  }, [open]);

  const items: [string, () => void][] = [
    ["Open console", onEnter],
    ["Marketplace", onEnter],
    ["Docs", onDocs],
  ];

  return (
    <div
      id="landing-menu"
      className={`fixed inset-0 z-40 bg-paper transition-opacity duration-500 ease-swift ${
        open ? "pointer-events-auto opacity-100" : "pointer-events-none opacity-0"
      }`}
    >
      <div className="gutter flex h-full flex-col justify-center gap-1">
        {items.map(([label, go], i) => (
          <button
            key={label}
            onClick={() => {
              onClose();
              go();
            }}
            style={{ transitionDelay: open ? `${i * 45}ms` : "0ms" }}
            className={`display-type text-left text-title text-ink transition-all duration-700 ease-enter ${
              open ? "translate-y-0 opacity-100" : "translate-y-3 opacity-0"
            }`}
          >
            {label}
          </button>
        ))}
      </div>
    </div>
  );
}

/* -- 01 hero ------------------------------------------------------------- */

/**
 * The first view is a single sentence at the largest scale the page ever uses,
 * uncovered line by line, with the mechanism diagram drifting behind it. The
 * product is introduced progressively: the headline first, its consequence
 * after, the controls last.
 */
function Hero({ onEnter, onDocs }: { onEnter: () => void; onDocs: () => void }) {
  const drift = useParallax<HTMLDivElement>(-0.06);
  const scrollTo = useScrollTo();

  return (
    <section className="relative flex min-h-[100svh] flex-col justify-between overflow-hidden pt-32 sm:pt-40">
      {/* The diagram sits behind the headline at low contrast, present enough
          to read as structure, quiet enough not to compete with the type. */}
      <div
        ref={drift}
        aria-hidden="true"
        className="pointer-events-none absolute inset-x-0 top-1/2 -z-0 hidden -translate-y-1/2 opacity-[0.07] lg:block"
      >
        <div className="gutter">
          <TransferDiagram />
        </div>
      </div>

      <div className="gutter relative z-10">
        <MaskLine>
          <p className="chapter-mark">01 / The property layer for agent memory</p>
        </MaskLine>

        <h1 className="display-type mt-10 text-colossal text-ink">
          <MaskLine index={0}>The code is</MaskLine>
          <MaskLine index={1}>replaceable.</MaskLine>
          <MaskLine index={2} className="text-faint">
            The memory is not.
          </MaskLine>
        </h1>
      </div>

      <div className="gutter relative z-10 pb-12">
        <div className="flex flex-col justify-between gap-10 border-t border-rule pt-8 lg:flex-row lg:items-end">
          <Reveal index={4}>
            <p className="max-w-measure text-lede text-muted">
              Succession turns an agent's accumulated memory into an asset that can be
              sold, verified, and settled on chain.
            </p>
          </Reveal>

          <Reveal index={5}>
            <div className="flex flex-wrap items-center gap-5">
              <Button onClick={onEnter}>Open console</Button>
              <Button variant="ghost" onClick={onDocs}>
                Read the docs
              </Button>
            </div>
          </Reveal>
        </div>

        <button
          onClick={() => scrollTo("#thesis")}
          className="mt-10 font-mono text-label uppercase text-faint transition-colors duration-500 hover:text-ink"
        >
          Scroll ↓
        </button>
      </div>
    </section>
  );
}

/* -- visual plates ------------------------------------------------------- */

/**
 * A full-bleed visual moment.
 *
 * The artwork is oversized inside a clipping frame so it has somewhere to
 * travel under parallax without exposing an edge, and it sits at low contrast
 * against the ground: these are compositions to move through, not illustrations
 * to stop and read. The caption is the only text allowed on them.
 */
function Plate({
  children,
  caption,
  tone = "paper",
  height = "h-[62vh] sm:h-[78vh]",
}: {
  children: ReactNode;
  caption: string;
  tone?: "paper" | "carbon";
  height?: string;
}) {
  const drift = useParallax<HTMLDivElement>(0.09);
  const dark = tone === "carbon";
  return (
    <section className={dark ? "on-carbon" : ""}>
      <figure className={`frame ${height} relative`}>
        <div ref={drift} className="absolute inset-0 -top-[8%] h-[116%]">
          <div className={dark ? "text-chalk/45 h-full" : "text-ink/25 h-full"}>
            {children}
          </div>
        </div>
        <figcaption className="gutter absolute bottom-0 left-0 right-0 pb-8">
          <p className={`chapter-mark ${dark ? "text-chalkFaint" : ""}`}>{caption}</p>
        </figcaption>
      </figure>
    </section>
  );
}

/* -- 02 thesis ----------------------------------------------------------- */

/**
 * One statement, given a whole viewport. The line is the argument, so nothing
 * shares the screen with it except the number and its own consequence.
 */
function Thesis() {
  return (
    <section id="thesis" className="gutter py-chapter">
      <Reveal>
        <p className="chapter-mark mb-16">02 / The thesis</p>
      </Reveal>

      <h2 className="display-type text-display text-ink">
        <MaskLine index={0}>The model is the employee.</MaskLine>
        <MaskLine index={1}>The memory is the customer book.</MaskLine>
      </h2>

      <Reveal index={2}>
        <p className="mt-14 max-w-measure border-l border-rule pl-6 text-lede text-muted lg:ml-auto">
          Succession does not sell the employee.
        </p>
      </Reveal>
    </section>
  );
}

/* -- 03 mechanism -------------------------------------------------------- */

/**
 * The first inversion. A full-bleed carbon chapter carrying the sale itself,
 * six ordered steps, set as a schedule rather than as a row of feature cards,
 * because the order is the whole guarantee.
 */
function Mechanism() {
  const steps = [
    ["Filter", "Withheld before hashing."],
    ["Commit", "Posted before a buyer exists."],
    ["Escrow", "Held by the contract."],
    ["Deliver", "Sealed. Key stays with the seller."],
    ["Re-hash", "Derived from the buyer's own store."],
    ["Settle", "One transaction, or none."],
  ];

  return (
    <section className="on-carbon py-chapter">
      <div className="gutter">
        <Reveal>
          <p className="chapter-mark mb-16">03 / How a sale works</p>
        </Reveal>

        <h2 className="display-type max-w-[18ch] text-title text-chalk">
          <MaskLine>Atomicity by ordering, not by assertion.</MaskLine>
        </h2>

        <ol className="mt-24 border-t border-carbonRule">
          {steps.map(([name, detail], i) => (
            <Reveal as="li" key={name} index={i % 3}>
              <div className="group flex flex-col gap-3 border-b border-carbonRule py-8 md:flex-row md:items-baseline md:gap-16">
                <span className="font-mono text-label uppercase text-chalkFaint md:w-16">
                  {String(i + 1).padStart(2, "0")}
                </span>
                <h3 className="display-type text-title text-chalk transition-transform duration-700 ease-swift md:w-[38%] md:group-hover:translate-x-2">
                  {name}
                </h3>
                <p className="max-w-measure text-body text-chalkMuted">{detail}</p>
              </div>
            </Reveal>
          ))}
        </ol>
      </div>
    </section>
  );
}

/* -- 04 verification ----------------------------------------------------- */

/**
 * The moment the product turns on, so it gets the page to itself: the diagram
 * at full width, and the argument for why re-hashing the destination is a
 * different claim from checking the bytes.
 */
function Verification() {
  return (
    <section className="gutter py-chapter">
      <Reveal>
        <p className="chapter-mark mb-16">04 / Verification</p>
      </Reveal>

      <div className="grid gap-16 lg:grid-cols-12 lg:gap-24">
        <div className="lg:col-span-5">
          <h2 className="display-type text-title text-ink">
            <MaskLine index={0}>Checked against</MaskLine>
            <MaskLine index={1}>the destination.</MaskLine>
          </h2>
          <Reveal index={2}>
            <p className="mt-8 max-w-measure text-lede text-muted">
              Not the bytes sent. The store that received them.
            </p>
          </Reveal>
        </div>

        <Reveal className="lg:col-span-7" index={1}>
          <HashVerification />
        </Reveal>
      </div>
    </section>
  );
}

/* -- pinned: the commitment ---------------------------------------------- */

/**
 * A pinned chapter, choreographed by scroll position rather than by time.
 *
 * The section is three viewports tall and its inner frame sticks for the whole
 * traversal, so the reader's scroll drives a sequence instead of moving past
 * it: the commitment is posted, a buyer appears, the delivered root is derived
 * and the two are compared. It is the argument of the product performed at the
 * speed the reader chooses, which is the one thing a static diagram cannot do.
 *
 * Progress is written straight to transforms in a rAF loop, never to React
 * state. A scroll-linked value that re-renders sixty times a second is a
 * scroll-linked value that drops frames.
 */
function Commitment() {
  const trackRef = useRef<HTMLDivElement | null>(null);
  const stepRefs = useRef<(HTMLLIElement | null)[]>([]);
  const barRef = useRef<HTMLSpanElement | null>(null);

  const steps = [
    ["Committed", "No buyer exists yet."],
    ["Escrowed", "Nothing has moved."],
    ["Delivered", "Imported, then re-hashed."],
    ["Verified", "Settled in one transaction."],
  ];

  const sceneRef = useScrollScene<HTMLElement>((p) => {
    // Ease the raw progress so the first and last steps hold a little longer
    // than the middle, the ends are where a reader arrives and leaves.
    const eased = Math.min(1, Math.max(0, (p - 0.12) / 0.72));
    if (barRef.current) barRef.current.style.transform = `scaleX(${eased})`;

    const active = Math.min(steps.length - 1, Math.floor(eased * steps.length));
    stepRefs.current.forEach((el, i) => {
      if (!el) return;
      const on = i <= active;
      el.style.opacity = on ? "1" : "0.22";
      el.style.transform = `translate3d(0, ${on ? 0 : 8}px, 0)`;
    });
    if (trackRef.current) {
      trackRef.current.style.transform = `translate3d(0, ${(0.5 - eased) * 40}px, 0)`;
    }
  });

  return (
    <section ref={sceneRef} className="on-carbon relative h-[300vh]">
      <div className="sticky top-0 flex h-screen flex-col justify-center overflow-hidden">
        <div className="gutter">
          <p className="chapter-mark mb-12">05 / The commitment, in order</p>

          <div ref={trackRef}>
            <h2 className="display-type max-w-[16ch] text-title text-chalk">
              The hash is posted before a buyer exists.
            </h2>

            <ol className="mt-16 grid gap-px border-y border-carbonRule bg-carbonRule sm:grid-cols-2 lg:grid-cols-4">
              {steps.map(([name, detail], i) => (
                <li
                  key={name}
                  ref={(el) => {
                    stepRefs.current[i] = el;
                  }}
                  className="bg-carbon px-6 py-10 transition-[opacity,transform] duration-500 ease-swift"
                  style={{ opacity: 0.22 }}
                >
                  <span className="font-mono text-label uppercase text-chalkFaint">
                    {String(i + 1).padStart(2, "0")}
                  </span>
                  <h3 className="display-type mt-4 text-heading text-chalk">{name}</h3>
                  <p className="mt-3 text-body text-chalkMuted">{detail}</p>
                </li>
              ))}
            </ol>

            {/* The reader's own position through the sequence, as a length. */}
            <span className="mt-12 block h-px w-full bg-carbonRule">
              <span
                ref={barRef}
                className="block h-px origin-left bg-chalk"
                style={{ transform: "scaleX(0)" }}
              />
            </span>
          </div>
        </div>
      </div>
    </section>
  );
}

/* -- 06 proof ------------------------------------------------------------ */

/** Figures at display scale, counted up once as they arrive. */
function Proof() {
  const tests = useCountUp(259);
  const contracts = useCountUp(28);

  return (
    <section className="gutter border-y border-rule py-beat">
      <Reveal>
        <p className="chapter-mark mb-14">05 / What is actually built</p>
      </Reveal>

      <div className="grid gap-14 sm:grid-cols-2 lg:grid-cols-4">
        <Reveal index={0}>
          <Figure value={<span ref={tests.ref}>{tests.shown}</span>} label="Python tests" />
        </Reveal>
        <Reveal index={1}>
          <Figure
            value={<span ref={contracts.ref}>{contracts.shown}</span>}
            label="Contract tests"
          />
        </Reveal>
        <Reveal index={2}>
          <Figure value="9" label="SMP directories" />
        </Reveal>
        <Reveal index={3}>
          <Figure value="1" label="Transaction to settle" tone="closed" />
        </Reveal>
      </div>
    </section>
  );
}

/* -- 06 stacks ----------------------------------------------------------- */

function Stacks() {
  const rows = [
    ["Sibyl Memory", "The asset itself."],
    ["Base", "Escrow and settlement."],
    ["ERC-8004", "Identity as a token."],
    ["Virtuals ACP", "Earnings a buyer can check."],
  ];

  return (
    <section className="gutter py-chapter">
      <Reveal>
        <p className="chapter-mark mb-16">06 / What it runs on</p>
      </Reveal>

      <dl className="border-t border-rule">
        {rows.map(([name, detail], i) => (
          <Reveal key={name} index={i % 3}>
            <div className="group flex flex-col gap-3 border-b border-rule py-10 md:flex-row md:items-baseline md:gap-16">
              <dt className="display-type text-title text-ink transition-transform duration-700 ease-swift md:w-[34%] md:group-hover:translate-x-2">
                {name}
              </dt>
              <dd className="max-w-measure text-body text-muted">{detail}</dd>
            </div>
          </Reveal>
        ))}
      </dl>
    </section>
  );
}

/* -- 07 lifecycle -------------------------------------------------------- */

/**
 * A horizontal rail. The lifecycle is a sequence with more entries than fit a
 * column comfortably, and reading it sideways makes the ordering legible in a
 * way a vertical list of eight items does not.
 */
function Lifecycle() {
  const railPointer = useCursorState("drag", "Drag");
  const items: [string, string, string][] = [
    ["Sell", "Built", "End to end."],
    ["Partial", "Built", "Some categories, not all."],
    ["Archive", "Free", "At tenant level."],
    ["Lease", "Designed", "An on-chain expiry."],
    ["Conditional", "Designed", "An oracle gate."],
    ["Inherit", "Roadmap", "A different trigger."],
    ["Merge", "Roadmap", "Two memories, one rule."],
    ["Split", "Roadmap", "The inverse of merge."],
  ];

  return (
    <section className="py-chapter">
      <div className="gutter">
        <Reveal>
          <p className="chapter-mark mb-16">07 / The lifecycle</p>
        </Reveal>
        <h2 className="display-type max-w-[20ch] text-title text-ink">
          <MaskLine>Selling is the first primitive, not the only one.</MaskLine>
        </h2>
      </div>

      <div className="rail mt-16 overflow-x-auto pb-4" {...railPointer}>
        <ul className="flex w-max gap-px border-y border-rule bg-rule">
          {items.map(([name, state, detail]) => (
            <li
              key={name}
              className="w-[19rem] shrink-0 bg-paper px-8 py-12 transition-colors duration-700 hover:bg-shade sm:w-[22rem]"
            >
              <p className="font-mono text-label uppercase text-faint">{state}</p>
              <h3 className="display-type mt-5 text-title text-ink">{name}</h3>
              <p className="mt-4 text-body text-muted">{detail}</p>
            </li>
          ))}
        </ul>
      </div>

      <div className="gutter mt-6">
        <p className="font-mono text-label uppercase text-faint">Scroll sideways →</p>
      </div>
    </section>
  );
}

/* -- 08 close ------------------------------------------------------------ */

function Close({ onEnter }: { onEnter: () => void }) {
  const drift = useParallax<HTMLDivElement>(0.05);
  return (
    <section className="on-carbon relative overflow-hidden py-chapter">
      <div ref={drift} className="gutter">
        <Reveal>
          <p className="chapter-mark mb-16">08 / Enter</p>
        </Reveal>

        <h2 className="display-type text-display text-chalk">
          <MaskLine index={0}>Memory that outlives</MaskLine>
          <MaskLine index={1}>the agent that made it.</MaskLine>
        </h2>

        <Reveal index={2}>
          <div className="mt-16 flex flex-wrap items-center gap-6">
            <button
              onClick={onEnter}
              className="border border-chalk bg-chalk px-10 py-4 font-mono text-micro uppercase tracking-[0.12em] text-carbon transition-colors duration-500 ease-swift hover:bg-transparent hover:text-chalk"
            >
              Open console
            </button>
            <p className="font-mono text-label uppercase text-chalkFaint">
              Listings are read from the contract
            </p>
          </div>
        </Reveal>
      </div>
    </section>
  );
}

/* -- colophon ------------------------------------------------------------ */

function Colophon({ onDocs }: { onDocs: () => void }) {
  return (
    <footer className="gutter py-beat">
      <div className="flex flex-col gap-6 border-t border-rule pt-8 sm:flex-row sm:items-center sm:justify-between">
        <p className="font-mono text-label uppercase text-faint">
          Succession · Base Sepolia · Sibyl Memory
        </p>
        <div className="flex gap-8">
          <button
            onClick={onDocs}
            className="link-underline font-mono text-label uppercase text-faint transition-colors duration-500 hover:text-ink"
          >
            Docs
          </button>
          <a
            href="https://github.com/linoxbt/Succession"
            target="_blank"
            rel="noreferrer"
            className="link-underline font-mono text-label uppercase text-faint transition-colors duration-500 hover:text-ink"
          >
            Source
          </a>
        </div>
      </div>
    </footer>
  );
}

export function Band({ label, children }: { label?: string; children: ReactNode }) {
  return (
    <section className="gutter py-beat">
      {label ? <p className="chapter-mark mb-10">{label}</p> : null}
      {children}
    </section>
  );
}
