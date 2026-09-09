export function LogoMark({ className = "" }: { className?: string }) {
  return (
    <svg viewBox="13 9 74 74" className={className} role="img" aria-label="Succession">
      <polygon points="50,10 68,28 50,46 32,28" fill="currentColor" />
      <polygon points="68.6,46 86.6,64 68.6,82 50.6,64" fill="currentColor" />
      <polygon points="31.4,46 49.4,64 31.4,82 13.4,64" fill="currentColor" />
    </svg>
  );
}

export function Wordmark({ className = "" }: { className?: string }) {
  return (
    <span className={`inline-flex items-center gap-1 font-mono font-bold tracking-tight ${className}`}>
      <LogoMark className="h-[1.6em] w-[1.6em] text-accent" />
      SUCCES<span className="text-accent">SION</span>
    </span>
  );
}
