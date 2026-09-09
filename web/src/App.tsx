/** The operator console: dashboard, guide, and a recording checklist. */
import { Landing } from "./landing/Landing";
import { to, useNavigation } from "./router";
import Shell from "./dash/Shell";
import Dashboard from "./dash/Dashboard";
import Guide from "./dash/Guide";
import TerminalDemo from "./dash/TerminalDemo";
import { CursorProvider, SmoothScroll } from "./motion";
import Cursor from "./chrome/Cursor";
import Preloader from "./chrome/Preloader";
import Transition from "./chrome/Transition";

export default function App() {
  return (
    <SmoothScroll>
      <CursorProvider>
        <Cursor />
        <Surface />
      </CursorProvider>
    </SmoothScroll>
  );
}

function Surface() {
  const { route, navigate } = useNavigation();

  if (route.kind === "landing") {
    return (
      <>
        <Preloader onDone={() => undefined} />
        <Landing
          onEnter={() => navigate(to.view("dashboard"))}
          onDocs={() => navigate(to.view("guide"))}
        />
      </>
    );
  }

  return (
    <Shell
      view={route.view}
      onView={(view) => navigate(to.view(view))}
      onHome={() => navigate(to.landing())}
    >
      <Transition routeKey={route.view}>
        {route.view === "dashboard" ? <Dashboard onGuide={() => navigate(to.view("guide"))} /> : null}
        {route.view === "guide" ? <Guide onTerminal={() => navigate(to.view("terminal"))} /> : null}
        {route.view === "terminal" ? <TerminalDemo /> : null}
      </Transition>
    </Shell>
  );
}
