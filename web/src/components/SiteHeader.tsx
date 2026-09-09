import { Wordmark } from "./Brand";
import { ThemeToggle } from "./Theme";
import { to, type AppView } from "../router";

export function SiteHeader({ navigate }: { navigate: (route: ReturnType<typeof to.view> | ReturnType<typeof to.landing>) => void }) {
  const links: { label: string; view?: AppView; hash?: string }[] = [
    { label: "How it works", hash: "pipeline" },
    { label: "Guides", view: "guide" },
    { label: "Video script", view: "terminal" },
    { label: "Dashboard", view: "dashboard" },
  ];
  return (
    <nav aria-label="Site" className="mx-auto flex max-w-5xl items-center justify-between border-b border-line px-6 py-6">
      <button onClick={() => navigate(to.landing())}><Wordmark className="text-lg" /></button>
      <div className="flex items-center gap-6 font-mono text-xs uppercase tracking-wide text-muted">
        {links.map((link) => (
          <button key={link.label} onClick={() => link.view ? navigate(to.view(link.view)) : document.getElementById(link.hash!)?.scrollIntoView({ behavior: "smooth" })}
            className="hidden hover:text-ink sm:inline">{link.label}</button>
        ))}
        <ThemeToggle />
        <button onClick={() => navigate(to.view("dashboard"))} className="rounded-sm border border-accent px-3 py-1.5 text-accent hover:bg-accent hover:text-bg">
          Open Dashboard
        </button>
      </div>
    </nav>
  );
}
