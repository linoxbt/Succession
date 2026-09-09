import { useState } from "react";
import { Check, Copy } from "lucide-react";
export function CopyableCodeBlock({ children }: { children: string }) {
  const [copied, setCopied] = useState(false);
  const [failed, setFailed] = useState(false);
  const handleCopy = async () => {
    try { await navigator.clipboard.writeText(children); setCopied(true); setFailed(false); setTimeout(() => setCopied(false), 1500); }
    catch { setFailed(true); setTimeout(() => setFailed(false), 2000); }
  };
  return (
    <div className="group relative">
      <pre className="overflow-x-auto rounded-sm border border-line bg-surface p-4 text-[12.5px] leading-relaxed"><code className="font-mono text-ink/90">{children}</code></pre>
      <button type="button" onClick={handleCopy} aria-label={failed ? "Copy failed" : "Copy to clipboard"}
        className="absolute right-2 top-2 inline-flex h-7 w-7 items-center justify-center rounded-sm border border-line bg-bg text-muted opacity-0 transition hover:text-accent focus-visible:opacity-100 group-hover:opacity-100 group-focus-within:opacity-100 [@media(hover:none)]:opacity-100">
        {failed ? <span className="text-[10px] text-fail">✕</span> : copied ? <Check size={14} className="text-pass" /> : <Copy size={14} />}
      </button>
    </div>
  );
}
