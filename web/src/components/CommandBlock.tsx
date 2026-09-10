import { Check, Copy } from "lucide-react";
import { useState } from "react";

export function CommandBlock({ children }: { children: string }) {
  const [copied, setCopied] = useState(false);
  const copy = async () => { await navigator.clipboard.writeText(children); setCopied(true); window.setTimeout(() => setCopied(false), 1200); };
  return <div className="relative mt-4 overflow-hidden rounded-md border border-foreground/15 bg-foreground p-4 text-background"><pre className="overflow-x-auto pr-10 font-mono text-xs leading-6"><code>{children}</code></pre><button aria-label="Copy to clipboard" onClick={copy} className="absolute right-2 top-2 rounded-md border border-background/20 bg-background/10 p-2 text-background hover:bg-background/20">{copied ? <Check className="h-4 w-4" /> : <Copy className="h-4 w-4" />}</button></div>;
}
