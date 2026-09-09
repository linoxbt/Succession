import { createContext, useContext, useEffect, useRef, useState, type ReactNode } from "react";
import { BookOpen, Clapperboard, LayoutDashboard, Menu, PanelLeft, PanelLeftClose, X } from "lucide-react";
import { Wordmark, LogoMark } from "./Brand";
import { ThemeToggle } from "./Theme";
import { to, type AppView } from "../router";

type Navigate = (route: ReturnType<typeof to.view> | ReturnType<typeof to.landing>) => void;
const SidebarContext = createContext<{ collapsed: boolean; mobile: boolean; toggleCollapsed: () => void; toggleMobile: () => void; close: () => void } | null>(null);
const nav: { view: AppView; label: string; eyebrow?: string; Icon: typeof LayoutDashboard }[] = [
  { view: "dashboard", label: "Dashboard", Icon: LayoutDashboard },
  { view: "guide", label: "Succession Guide", eyebrow: "guide", Icon: BookOpen },
  { view: "terminal", label: "Video Runbook", eyebrow: "guide", Icon: Clapperboard },
];

function Provider({ children }: { children: ReactNode }) {
  const [collapsed, setCollapsed] = useState(() => localStorage.getItem("succession:sidebar-collapsed") === "1");
  const [mobile, setMobile] = useState(false);
  useEffect(() => {
    const media = matchMedia("(min-width: 768px)");
    const change = () => { if (media.matches) setMobile(false); };
    media.addEventListener("change", change);
    return () => media.removeEventListener("change", change);
  }, []);
  const toggleCollapsed = () => setCollapsed((value) => { localStorage.setItem("succession:sidebar-collapsed", value ? "0" : "1"); return !value; });
  return <SidebarContext.Provider value={{ collapsed, mobile, toggleCollapsed, toggleMobile: () => setMobile((v) => !v), close: () => setMobile(false) }}>{children}</SidebarContext.Provider>;
}

function NavLinks({ current, navigate, collapsed, close }: { current: AppView; navigate: Navigate; collapsed: boolean; close?: () => void }) {
  return <nav aria-label="Primary" className="flex flex-col gap-1">{nav.map(({ view, label, eyebrow, Icon }) => (
    <button key={view} onClick={() => { navigate(to.view(view)); close?.(); }} title={collapsed ? label : undefined}
      className={`flex items-center gap-3 rounded-sm px-3 py-2 text-sm transition ${current === view ? "bg-accent/10 font-medium text-accent" : "text-ink/75 hover:bg-surface"} ${collapsed ? "justify-center" : ""}`}>
      <Icon size={16} className="flex-none" />
      {!collapsed && <span>{eyebrow && <span className="mr-2 font-mono text-[10px] uppercase tracking-wide text-muted">{eyebrow}</span>}{label}</span>}
    </button>
  ))}</nav>;
}

function Sidebar({ current, navigate }: { current: AppView; navigate: Navigate }) {
  const state = useContext(SidebarContext)!;
  return (
    <>
      <aside className={`hidden flex-none flex-col border-r border-line px-4 py-6 transition-all duration-200 md:flex ${state.collapsed ? "w-20 items-center" : "w-64"}`}>
        <div className={`mb-8 flex items-center ${state.collapsed ? "justify-center" : "justify-between"} px-2`}>
          <button onClick={() => navigate(to.landing())}>{state.collapsed ? <LogoMark className="h-6 w-6 text-accent" /> : <Wordmark className="text-base" />}</button>
        </div>
        {!state.collapsed && <p className="mb-3 px-3 font-mono text-[11px] uppercase tracking-widest text-muted">Succession</p>}
        <NavLinks current={current} navigate={navigate} collapsed={state.collapsed} />
        <div className={`mt-auto flex flex-col gap-3 pt-8 ${state.collapsed ? "items-center" : ""}`}>
          <button type="button" onClick={state.toggleCollapsed} aria-label={state.collapsed ? "Expand sidebar" : "Collapse sidebar"}
            className="inline-flex h-8 w-8 items-center justify-center rounded-sm border border-line text-ink/75 transition hover:border-accent/50 hover:text-accent">
            {state.collapsed ? <PanelLeft size={16} /> : <PanelLeftClose size={16} />}
          </button>
          <ThemeToggle />
          {!state.collapsed && <div className="flex flex-col gap-1"><button onClick={() => navigate(to.view("guide"))} className="text-left font-mono text-xs text-muted hover:text-ink">Docs →</button><button onClick={() => navigate(to.landing())} className="text-left font-mono text-xs text-muted hover:text-ink">← Back to site</button></div>}
        </div>
      </aside>
      <MobileDrawer current={current} navigate={navigate} />
    </>
  );
}

function MobileDrawer({ current, navigate }: { current: AppView; navigate: Navigate }) {
  const state = useContext(SidebarContext)!;
  const ref = useRef<HTMLElement>(null);
  useEffect(() => {
    if (!state.mobile) return;
    const focusable = ref.current?.querySelectorAll<HTMLElement>('button:not([disabled])');
    focusable?.[0]?.focus();
    const key = (event: KeyboardEvent) => {
      if (event.key === "Escape") state.close();
      if (event.key !== "Tab" || !focusable?.length) return;
      const first = focusable[0]!; const last = focusable[focusable.length - 1]!;
      if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last.focus(); }
      else if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first.focus(); }
    };
    document.addEventListener("keydown", key);
    return () => document.removeEventListener("keydown", key);
  }, [state.mobile]);
  return <><div onClick={state.close} aria-hidden="true" className={`fixed inset-0 z-40 bg-black/50 transition-opacity md:hidden ${state.mobile ? "opacity-100" : "pointer-events-none opacity-0"}`} />
    <aside ref={ref} role="dialog" aria-modal="true" aria-label="Mobile navigation" className={`fixed inset-y-0 left-0 z-50 flex w-72 flex-col border-r border-line bg-bg px-4 py-6 transition-transform duration-200 md:hidden ${state.mobile ? "translate-x-0" : "-translate-x-full"}`}>
      <div className="mb-8 flex items-center justify-between px-2"><button onClick={() => navigate(to.landing())}><Wordmark className="text-base" /></button><button onClick={state.close} aria-label="Close menu" className="text-ink/75"><X size={18} /></button></div>
      <p className="mb-3 px-3 font-mono text-[11px] uppercase tracking-widest text-muted">Succession</p>
      <NavLinks current={current} navigate={navigate} collapsed={false} close={state.close} />
      <div className="mt-auto flex flex-col gap-3 pt-8"><ThemeToggle /><button onClick={() => navigate(to.landing())} className="text-left font-mono text-xs text-muted hover:text-ink">← Back to site</button></div>
    </aside></>;
}

function MobileTopBar({ navigate }: { navigate: Navigate }) {
  const state = useContext(SidebarContext)!;
  return <div className="flex items-center justify-between border-b border-line px-6 py-4 md:hidden"><button onClick={() => navigate(to.landing())}><Wordmark className="text-base" /></button><button onClick={state.toggleMobile} aria-label="Open menu" className="text-ink/75"><Menu size={20} /></button></div>;
}

export function DashboardLayout({ current, navigate, children }: { current: AppView; navigate: Navigate; children: ReactNode }) {
  return <Provider><div className="flex min-h-screen"><Sidebar current={current} navigate={navigate} /><div className="flex min-w-0 flex-1 flex-col"><MobileTopBar navigate={navigate} /><main className="min-w-0 flex-1 px-6 py-10 md:px-10">{children}</main></div></div></Provider>;
}
