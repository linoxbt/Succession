import { DashboardLayout } from "./components/DashboardLayout";
import { Landing } from "./landing/Landing";
import Dashboard from "./dash/Dashboard";
import Guide from "./dash/Guide";
import TerminalDemo from "./dash/TerminalDemo";
import { useNavigation } from "./router";

export default function App() {
  const { route, navigate } = useNavigation();
  if (route.kind === "landing") return <Landing navigate={navigate} />;
  if (route.view === "guide") return <Guide navigate={navigate} />;
  if (route.view === "terminal") return <TerminalDemo navigate={navigate} />;
  return <DashboardLayout current={route.view} navigate={navigate}><Dashboard navigate={navigate} /></DashboardLayout>;
}
