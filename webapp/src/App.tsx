import { HashRouter, Route, Routes } from "react-router-dom";
import Layout from "./Layout";
import Apps from "./pages/Apps";
import Chat from "./pages/Chat";
import Dashboard from "./pages/Dashboard";
import Documents from "./pages/Documents";
import Help from "./pages/Help";
import Logs from "./pages/Logs";
import Onboarding from "./pages/Onboarding";
import SettingsPage from "./pages/Settings";
import Skills from "./pages/Skills";
import Stitcher from "./pages/Stitcher";
import Sync from "./pages/Sync";
import Tools from "./pages/Tools";

export default function App() {
  return (
    <HashRouter>
      <Routes>
        <Route element={<Layout />}>
          <Route index element={<Dashboard />} />
          <Route path="documents" element={<Documents />} />
          <Route path="stitcher" element={<Stitcher />} />
          <Route path="sync" element={<Sync />} />
          <Route path="tools" element={<Tools />} />
          <Route path="skills" element={<Skills />} />
          <Route path="chat" element={<Chat />} />
          <Route path="apps" element={<Apps />} />
          <Route path="onboarding" element={<Onboarding />} />
          <Route path="settings" element={<SettingsPage />} />
          <Route path="help" element={<Help />} />
          <Route path="logs" element={<Logs />} />
        </Route>
      </Routes>
    </HashRouter>
  );
}
