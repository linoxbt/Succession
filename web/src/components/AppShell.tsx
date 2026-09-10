import { BookOpen, Clapperboard, LayoutDashboard, ShieldCheck } from "lucide-react";
import { to, type AppView } from "../router";
import type { ReactNode } from "react";

type Navigate = (route: ReturnType<typeof to.view> | ReturnType<typeof to.landing>) => void;
const nav = [
  { view: "dashboard" as const, label: "Dashboard", Icon: LayoutDashboard },
  { view: "guide" as const, label: "Guide", Icon: BookOpen },
  { view: "terminal" as const, label: "Video Script", Icon: Clapperboard },
];

export function SuccessionLogo({ compact = false }: { compact?: boolean }) {
  return <span className="flex items-center gap-3"><span className="relative grid h-9 w-9 place-items-center rounded-md border border-current/50 bg-current/10 shadow-glow"><span className="absolute inset-1 rounded-sm border border-current/70" /><span className="h-3 w-3 rotate-45 border-2 border-current bg-background" /></span>{!compact && <span className="leading-none"><span className="block text-lg font-black tracking-normal text-current">Succession</span></span>}</span>;
}

export function LogoMark({ navigate }: { navigate: Navigate }) {
  return <button onClick={() => navigate(to.landing())} className="group flex items-center gap-3 focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2 focus:ring-offset-background"><SuccessionLogo /></button>;
}

export function StatusBadge({ status, label }: { status: "live" | "pending" | "failed"; label?: string }) {
  return <span className={`inline-flex items-center gap-2 rounded-full border px-2.5 py-1 text-xs font-semibold ${status === "live" ? "border-success/30 bg-success/10 text-success" : status === "failed" ? "border-destructive/30 bg-destructive/10 text-destructive" : "border-warning/30 bg-warning/10 text-warning"}`}><span className="h-1.5 w-1.5 rounded-full bg-current" />{label ?? status.charAt(0).toUpperCase() + status.slice(1)}</span>;
}

export function AppShell({ current, navigate, evaluator, children }: { current: AppView; navigate: Navigate; evaluator?: string; children: ReactNode }) {
  return <div className="min-h-screen bg-background text-foreground"><div className="fixed inset-0 -z-10 bg-grid opacity-90" />
    <aside className="fixed left-0 top-0 z-20 hidden h-screen w-64 border-r border-border bg-sidebar px-4 py-5 text-sidebar-foreground lg:block">
      <LogoMark navigate={navigate} />
      <nav className="mt-10 space-y-2">{nav.map(({view,label,Icon}) => <button key={view} onClick={() => navigate(to.view(view))} className={`flex w-full items-center gap-3 rounded-md border-l-2 px-3 py-2.5 text-sm font-bold transition ${current === view ? "border-sidebar-foreground bg-sidebar-foreground/10 text-sidebar-foreground" : "border-transparent text-sidebar-foreground/60 hover:bg-sidebar-foreground/10 hover:text-sidebar-foreground"}`}><Icon className="h-4 w-4" />{label}</button>)}</nav>
      <div className="absolute bottom-5 left-4 right-4 rounded-md border border-sidebar-foreground/15 bg-sidebar-foreground/10 p-3"><div className="flex items-center gap-3"><div className="flex h-9 w-9 items-center justify-center rounded-md bg-sidebar-foreground text-sidebar"><ShieldCheck className="h-4 w-4" /></div><div className="min-w-0 flex-1"><p className="text-sm font-semibold text-sidebar-foreground">Evaluator custody</p><p className="truncate font-mono text-xs text-sidebar-foreground/60">{evaluator ?? "Loading address…"}</p></div></div><button onClick={() => navigate(to.view("guide"))} className="mt-3 block w-full rounded-md bg-sidebar-foreground px-3 py-2 text-center text-xs font-extrabold text-sidebar transition hover:opacity-90">Deployment details</button></div>
    </aside>
    <main className="pb-20 lg:pl-64 lg:pb-0"><header className="sticky top-0 z-10 flex items-center justify-between border-b border-border bg-background/85 px-5 py-3 backdrop-blur lg:hidden"><LogoMark navigate={navigate} /><button onClick={() => navigate(to.view("guide"))} className="rounded-md border border-border px-3 py-2 text-xs font-bold">Guide</button></header><div className="hidden justify-end border-b border-border bg-background/70 px-8 py-3 backdrop-blur lg:flex"><button onClick={() => navigate(to.view("guide"))} className="rounded-md border border-border bg-card px-4 py-2 text-sm font-bold text-foreground transition hover:border-primary">Base Sepolia · Operator guide</button></div>{children}</main>
    <nav className="fixed bottom-0 left-0 right-0 z-30 grid grid-cols-3 border-t border-border bg-sidebar px-2 py-2 text-sidebar-foreground lg:hidden">{nav.map(({view,label,Icon}) => <button key={view} onClick={() => navigate(to.view(view))} className={`flex flex-col items-center gap-1 rounded-md px-2 py-1.5 text-xs ${current === view ? "text-sidebar-foreground" : "text-sidebar-foreground/55"}`}><Icon className="h-4 w-4" />{label}</button>)}</nav>
  </div>;
}
