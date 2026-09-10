import { Dashboard } from "./dash/Dashboard";
import { Docs } from "./dash/Docs";
import { Guide } from "./dash/Guide";
import { Landing } from "./landing/Landing";
import { useNavigation } from "./router";

export default function App() {
  const { route, navigate } = useNavigation();
  if (route.kind === "landing") return <Landing navigate={navigate} />;
  if (route.view === "guide") return <Guide navigate={navigate} />;
  if (route.view === "docs") return <Docs navigate={navigate} />;
  return <Dashboard navigate={navigate} />;
}
