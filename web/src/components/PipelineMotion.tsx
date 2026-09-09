import { motion } from "framer-motion";

const stages = [
  { label: "Package", detail: "filter · sign · encrypt" },
  { label: "Verify", detail: "import · re-hash" },
  { label: "Settle", detail: "Base · ERC-8004" },
];
const container = { hidden: {}, show: { transition: { staggerChildren: .35, delayChildren: .15 } } };
const node = { hidden: { opacity: 0, scale: .85 }, show: { opacity: 1, scale: 1, transition: { duration: .5, ease: [0.16, 1, 0.3, 1] as const } } };
const line = { hidden: { scaleX: 0 }, show: { scaleX: 1, transition: { duration: .5, ease: [0.16, 1, 0.3, 1] as const } } };

export function PipelineMotion() {
  return (
    <motion.div variants={container} initial="hidden" whileInView="show" viewport={{ once: true, amount: .6 }} className="flex items-center" aria-hidden="true">
      {stages.map((stage, index) => (
        <div key={stage.label} className="flex items-center">
          {index > 0 && <motion.div variants={line} style={{ transformOrigin: "left" }} className="h-px w-8 bg-accent/40 md:w-14" />}
          <motion.div variants={node} className="flex flex-col items-center gap-2 px-1">
            <div className="flex h-14 w-14 items-center justify-center rounded-full border border-accent/50 bg-accent/10 font-mono text-[10px] font-bold uppercase tracking-wide text-accent md:h-16 md:w-16">{index + 1}</div>
            <div className="text-center"><p className="font-display text-sm font-bold">{stage.label}</p><p className="whitespace-nowrap font-mono text-[10px] text-muted">{stage.detail}</p></div>
          </motion.div>
        </div>
      ))}
    </motion.div>
  );
}
