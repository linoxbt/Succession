import { createContext, useContext, useState, type ReactNode } from "react";
import { Moon, Sun } from "lucide-react";

type Theme = "light" | "dark";
const ThemeContext = createContext<{ theme: Theme; toggle: () => void } | null>(null);
const KEY = "succession:theme";

export function ThemeProvider({ children }: { children: ReactNode }) {
  const [theme, setTheme] = useState<Theme>(() => document.documentElement.dataset.theme === "light" ? "light" : "dark");
  const toggle = () => setTheme((previous) => {
    const next = previous === "light" ? "dark" : "light";
    document.documentElement.dataset.theme = next;
    localStorage.setItem(KEY, next);
    return next;
  });
  return <ThemeContext.Provider value={{ theme, toggle }}>{children}</ThemeContext.Provider>;
}

export function ThemeToggle({ className = "" }: { className?: string }) {
  const context = useContext(ThemeContext);
  if (!context) throw new Error("ThemeToggle requires ThemeProvider");
  return (
    <button type="button" onClick={context.toggle} aria-label={context.theme === "light" ? "Switch to dark theme" : "Switch to light theme"}
      className={`inline-flex h-8 w-8 items-center justify-center rounded-sm border border-line text-ink/75 transition hover:border-accent/50 hover:text-accent ${className}`}>
      {context.theme === "light" ? <Moon size={16} /> : <Sun size={16} />}
    </button>
  );
}
