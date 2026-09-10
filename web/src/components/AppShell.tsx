import { BookOpen, Database, FileText, LayoutDashboard } from "lucide-react";
import { to, type AppView } from "../router";
import type { ReactNode } from "react";

type Navigate = (route: ReturnType<typeof to.view> | ReturnType<typeof to.landing>) => void;
const nav = [
  { view: "dashboard" as const, label: "Dashboard", Icon: LayoutDashboard },
  { view: "guide" as const, label: "Guide", Icon: BookOpen },
  { view: "docs" as const, label: "Docs", Icon: FileText },
];

export function SuccessionLogo({ compact = false }: { compact?: boolean }) {
  return <span className="flex items-center gap-3"><svg aria-hidden="true" viewBox="0 0 32 32" className="h-9 w-9 shrink-0 rounded-lg shadow-glow"><rect width="32" height="32" rx="8" fill="#011B33"/><g transform="translate(3.2 3.2) scale(.8)" fill="none" strokeLinecap="round" strokeWidth="3.6"><path d="M23.5 10.5C23.5 5.5 8.5 5.5 8.5 12.5C8.5 19.5 23.5 12.5 23.5 19.5C23.5 26.5 8.5 26.5 8.5 21.5" pathLength="100" stroke="#fff" strokeDasharray="46 100"/><path d="M23.5 10.5C23.5 5.5 8.5 5.5 8.5 12.5C8.5 19.5 23.5 12.5 23.5 19.5C23.5 26.5 8.5 26.5 8.5 21.5" pathLength="100" stroke="#00C3F7" strokeDasharray="46 100" strokeDashoffset="-54"/></g></svg>{!compact && <span className="text-lg font-black leading-none tracking-normal text-current">Succession</span>}</span>;
}

export function LogoMark({ navigate }: { navigate: Navigate }) {
  return <button onClick={() => navigate(to.landing())} className="group flex items-center gap-3 focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2 focus:ring-offset-background"><SuccessionLogo /></button>;
}

export function StatusBadge({ status, label }: { status: "live" | "pending" | "failed"; label?: string }) {
  return <span className={`inline-flex items-center gap-2 rounded-full border px-2.5 py-1 text-xs font-semibold ${status === "live" ? "border-success/30 bg-success/10 text-success" : status === "failed" ? "border-destructive/30 bg-destructive/10 text-destructive" : "border-warning/30 bg-warning/10 text-warning"}`}><span className="h-1.5 w-1.5 rounded-full bg-current" />{label ?? status.charAt(0).toUpperCase() + status.slice(1)}</span>;
}

export function AppShell({ current, navigate, children }: { current: AppView; navigate: Navigate; children: ReactNode }) {
  return <div className="min-h-screen bg-background text-foreground"><div className="fixed inset-0 -z-10 bg-grid opacity-90" />
    <aside className="fixed left-0 top-0 z-20 hidden h-screen w-64 border-r border-border bg-sidebar px-4 py-5 text-sidebar-foreground lg:block">
      <LogoMark navigate={navigate} />
      <div className="mt-5 flex items-center gap-2 rounded-md border border-sidebar-foreground/15 bg-sidebar-foreground/5 px-3 py-2 text-xs font-bold text-sidebar-foreground/70"><Database className="h-3.5 w-3.5 text-primary" />Built on Sibyl Memory</div>
      <nav className="mt-10 space-y-2">{nav.map(({view,label,Icon}) => <button key={view} onClick={() => navigate(to.view(view))} className={`flex w-full items-center gap-3 rounded-md border-l-2 px-3 py-2.5 text-sm font-bold transition ${current === view ? "border-sidebar-foreground bg-sidebar-foreground/10 text-sidebar-foreground" : "border-transparent text-sidebar-foreground/60 hover:bg-sidebar-foreground/10 hover:text-sidebar-foreground"}`}><Icon className="h-4 w-4" />{label}</button>)}</nav>
      <div className="absolute bottom-5 left-4 right-4 rounded-md border border-sidebar-foreground/15 bg-sidebar-foreground/10 p-4"><p className="text-sm font-bold">New to Succession?</p><p className="mt-1 text-xs leading-5 text-sidebar-foreground/60">Install the CLI and complete your first verified memory transfer.</p><button onClick={() => navigate(to.view("guide"))} className="mt-3 block w-full rounded-md bg-sidebar-foreground px-3 py-2 text-center text-xs font-extrabold text-sidebar transition hover:opacity-90">Start the guide</button></div>
    </aside>
    <main className="pb-20 lg:pl-64 lg:pb-0"><header className="sticky top-0 z-10 flex items-center justify-between border-b border-border bg-background/85 px-5 py-3 backdrop-blur lg:hidden"><LogoMark navigate={navigate} /><button onClick={() => navigate(to.view("guide"))} className="rounded-md border border-border px-3 py-2 text-xs font-bold">Guide</button></header>{children}</main>
    <nav className="fixed bottom-0 left-0 right-0 z-30 grid grid-cols-3 border-t border-border bg-sidebar px-2 py-2 text-sidebar-foreground lg:hidden">{nav.map(({view,label,Icon}) => <button key={view} onClick={() => navigate(to.view(view))} className={`flex flex-col items-center gap-1 rounded-md px-2 py-1.5 text-xs ${current === view ? "text-sidebar-foreground" : "text-sidebar-foreground/55"}`}><Icon className="h-4 w-4" />{label}</button>)}</nav>
  </div>;
}
