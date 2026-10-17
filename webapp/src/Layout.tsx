import {
  BookOpen,
  ChevronLeft,
  ChevronRight,
  Circle,
  FileText,
  FolderSync,
  HelpCircle,
  Layers,
  LayoutDashboard,
  LayoutGrid,
  MessageSquare,
  ScrollText,
  Settings,
  Wrench,
} from "lucide-react";
import { useEffect, useState } from "react";
import { NavLink, Outlet } from "react-router-dom";
import { api } from "./lib/api";

const NAV = [
  { to: "/", label: "Dashboard", icon: LayoutDashboard },
  { to: "/documents", label: "Documents", icon: FileText },
  { to: "/stitcher", label: "Stitcher", icon: Layers },
  { to: "/sync", label: "Sync", icon: FolderSync },
  { to: "/tools", label: "Tools", icon: Wrench },
  { to: "/skills", label: "Skills", icon: BookOpen },
  { to: "/chat", label: "Chat", icon: MessageSquare },
  { to: "/apps", label: "Apps", icon: LayoutGrid },
  { to: "/settings", label: "Settings", icon: Settings },
  { to: "/help", label: "Help", icon: HelpCircle },
  { to: "/logs", label: "Logs", icon: ScrollText },
];

export default function Layout() {
  const [collapsed, setCollapsed] = useState(false);
  const [healthy, setHealthy] = useState<boolean | null>(null);

  useEffect(() => {
    api
      .health()
      .then(() => setHealthy(true))
      .catch(() => setHealthy(false));
  }, []);

  return (
    <div className="flex h-screen bg-surface text-zinc-100">
      <aside
        className={`flex flex-col border-r border-zinc-800 bg-panel transition-all ${
          collapsed ? "w-16" : "w-56"
        }`}
      >
        <div className="flex items-center justify-between px-3 py-4">
          {!collapsed && (
            <span className="font-semibold text-zinc-100">google-docs-mcp</span>
          )}
          <button
            type="button"
            data-testid="sidebar-collapse-toggle"
            onClick={() => setCollapsed((c) => !c)}
            className="rounded p-1 text-zinc-400 hover:bg-zinc-800 hover:text-zinc-100"
          >
            {collapsed ? <ChevronRight size={18} /> : <ChevronLeft size={18} />}
          </button>
        </div>
        <nav className="flex-1 space-y-1 px-2">
          {NAV.map(({ to, label, icon: Icon }) => (
            <NavLink
              key={to}
              to={to}
              end={to === "/"}
              data-testid={`nav-${label.toLowerCase()}`}
              className={({ isActive }) =>
                `flex items-center gap-3 rounded-lg px-3 py-2 text-sm transition-colors ${
                  isActive
                    ? "bg-amber-500/10 text-amber-400"
                    : "text-zinc-400 hover:bg-zinc-800 hover:text-zinc-100"
                }`
              }
            >
              <Icon size={18} />
              {!collapsed && <span>{label}</span>}
            </NavLink>
          ))}
        </nav>
      </aside>

      <div className="flex flex-1 flex-col overflow-hidden">
        <header className="flex items-center justify-between border-b border-zinc-800 bg-panel px-6 py-3">
          <div className="text-sm text-zinc-400">
            Google Docs / Drive MCP Dashboard
          </div>
          <div
            className="flex items-center gap-2 text-sm"
            data-testid="backend-health-dot"
          >
            <Circle
              size={10}
              className={
                healthy === null
                  ? "text-zinc-500"
                  : healthy
                    ? "fill-emerald-500 text-emerald-500"
                    : "fill-red-500 text-red-500"
              }
            />
            <span className="text-zinc-400">
              {healthy === null
                ? "Checking…"
                : healthy
                  ? "Backend online"
                  : "Backend offline"}
            </span>
          </div>
        </header>
        <main className="flex-1 overflow-y-auto p-6">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
