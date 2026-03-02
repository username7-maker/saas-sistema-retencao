import {
  Activity,
  Bell,
  Bot,
  Briefcase,
  ChevronDown,
  ChevronRight,
  ClipboardList,
  CheckSquare,
  FileText,
  LayoutDashboard,
  LogOut,
  Menu,
  Moon,
  ScrollText,
  Settings,
  ShieldAlert,
  Star,
  Sun,
  Target,
  Upload,
  UserCog,
  UserSquare2,
  Users,
  Wallet,
} from "lucide-react";
import type { LucideIcon } from "lucide-react";
import { useEffect, useState } from "react";
import { Link, NavLink, Outlet, useLocation, useNavigate } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";

import { useAuth } from "../../hooks/useAuth";
import { useTheme } from "../../hooks/useTheme";
import { notificationService } from "../../services/notificationService";
import { Button, Drawer, cn } from "../ui2";

interface NavItem {
  to: string;
  label: string;
  icon: LucideIcon;
}

interface NavGroup {
  label: string;
  items: NavItem[];
}

const navGroups: NavGroup[] = [
  {
    label: "Dashboards",
    items: [
      { to: "/dashboard/executive", label: "Executivo", icon: LayoutDashboard },
      { to: "/dashboard/operational", label: "Operacional", icon: Activity },
      { to: "/dashboard/commercial", label: "Comercial", icon: Briefcase },
      { to: "/dashboard/financial", label: "Financeiro", icon: Wallet },
      { to: "/dashboard/retention", label: "Retenção", icon: ShieldAlert },
    ],
  },
  {
    label: "Gestão",
    items: [
      { to: "/members", label: "Membros", icon: UserSquare2 },
      { to: "/assessments", label: "Avaliações", icon: ClipboardList },
      { to: "/crm", label: "CRM", icon: Users },
      { to: "/tasks", label: "Tarefas", icon: CheckSquare },
    ],
  },
  {
    label: "Resultados",
    items: [
      { to: "/goals", label: "Metas", icon: Target },
      { to: "/nps", label: "NPS", icon: Star },
      { to: "/reports", label: "Relatórios", icon: FileText },
    ],
  },
  {
    label: "Sistema",
    items: [
      { to: "/automations", label: "Automações", icon: Bot },
      { to: "/imports", label: "Importações", icon: Upload },
      { to: "/audit", label: "Auditoria", icon: ScrollText },
    ],
  },
  {
    label: "Admin",
    items: [
      { to: "/settings/users", label: "Usuários", icon: UserCog },
      { to: "/settings", label: "Configurações", icon: Settings },
    ],
  },
];

function resolveActiveGroup(pathname: string): string | null {
  for (const group of navGroups) {
    if (group.items.some((item) => pathname.startsWith(item.to))) {
      return group.label;
    }
  }
  return null;
}

function SidebarNav({ onNavigate }: { onNavigate?: () => void }) {
  const { pathname } = useLocation();
  const activeGroup = resolveActiveGroup(pathname);
  const [openGroups, setOpenGroups] = useState<string[]>(activeGroup ? [activeGroup] : ["Dashboards"]);

  useEffect(() => {
    if (activeGroup && !openGroups.includes(activeGroup)) {
      setOpenGroups((prev) => [...prev, activeGroup]);
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activeGroup]);

  function toggleGroup(label: string) {
    setOpenGroups((prev) =>
      prev.includes(label) ? prev.filter((g) => g !== label) : [...prev, label],
    );
  }

  return (
    <nav className="space-y-0.5 px-3 py-4">
      {navGroups.map((group) => {
        const isOpen = openGroups.includes(group.label);
        const ChevronIcon = isOpen ? ChevronDown : ChevronRight;
        return (
          <div key={group.label}>
            <button
              type="button"
              onClick={() => toggleGroup(group.label)}
              className="flex w-full items-center justify-between rounded-xl px-3 py-2 text-xs font-semibold uppercase tracking-wider text-lovable-ink-muted transition hover:bg-lovable-surface-soft hover:text-lovable-ink"
            >
              {group.label}
              <ChevronIcon size={13} />
            </button>
            {isOpen && (
              <div className="mt-0.5 mb-1 space-y-0.5 pl-2">
                {group.items.map((item) => {
                  const Icon = item.icon;
                  return (
                    <NavLink
                      key={item.to}
                      to={item.to}
                      onClick={onNavigate}
                      className={({ isActive }) =>
                        cn(
                          "flex items-center gap-3 rounded-xl px-3 py-2 text-sm font-medium transition",
                          isActive
                            ? "bg-lovable-primary text-white shadow-md"
                            : "text-lovable-ink-muted hover:bg-lovable-primary-soft/60 hover:text-lovable-ink",
                        )
                      }
                    >
                      <Icon size={16} />
                      <span>{item.label}</span>
                    </NavLink>
                  );
                })}
              </div>
            )}
          </div>
        );
      })}
    </nav>
  );
}

function resolveCurrentSection(pathname: string): string {
  for (const group of navGroups) {
    const item = group.items.find((candidate) => pathname.startsWith(candidate.to));
    if (item) return item.label;
  }
  return "AI GYM OS";
}

export function LovableLayout() {
  const { user, logout } = useAuth();
  const { theme, toggleTheme } = useTheme();
  const { pathname } = useLocation();
  const navigate = useNavigate();
  const currentSection = resolveCurrentSection(pathname);
  const [mobileOpen, setMobileOpen] = useState(false);

  const { data: notifications } = useQuery({
    queryKey: ["notifications", "unread-count"],
    queryFn: () => notificationService.listNotifications({ unread_only: false }),
    refetchInterval: 60_000,
  });
  const unreadCount = notifications?.items.filter((item) => !item.read_at).length ?? 0;

  return (
    <div className="min-h-screen bg-lovable-bg text-lovable-ink">
      <aside aria-label="Navegação principal" className="fixed inset-y-0 left-0 z-30 hidden w-72 border-r border-lovable-border bg-lovable-surface lg:block">
        <div className="border-b border-lovable-border px-6 py-5">
          <Link to="/dashboard/executive" aria-label="Ir para o dashboard" className="font-display text-2xl font-bold tracking-tight text-lovable-primary">
            AI GYM OS
          </Link>
          <p className="mt-1 text-xs uppercase tracking-widest text-lovable-ink-muted">Retention Intelligence</p>
        </div>
        <SidebarNav />
      </aside>

      <Drawer open={mobileOpen} onClose={() => setMobileOpen(false)} title="AI GYM OS">
        <SidebarNav onNavigate={() => setMobileOpen(false)} />
      </Drawer>

      <div className="lg:pl-72">
        <header role="banner" className="sticky top-0 z-20 border-b border-lovable-border bg-lovable-surface/90 px-4 py-3 backdrop-blur md:px-6">
          <div className="flex items-center justify-between gap-3">
            <div className="flex items-center gap-2">
              <Button variant="ghost" size="sm" className="lg:hidden" onClick={() => setMobileOpen(true)} aria-label="Abrir menu de navegação">
                <Menu size={16} />
              </Button>
              <div>
                <p className="text-xs uppercase tracking-[0.15em] text-lovable-ink-muted">Módulo Atual</p>
                <h1 className="font-display text-xl font-semibold text-lovable-ink">{currentSection}</h1>
              </div>
            </div>

            <div className="flex items-center gap-2">
              <Button
                variant="ghost"
                size="sm"
                onClick={toggleTheme}
                title={theme === "dark" ? "Modo claro" : "Modo escuro"}
              >
                {theme === "dark" ? <Sun size={16} /> : <Moon size={16} />}
              </Button>

              <button
                type="button"
                onClick={() => navigate("/notifications")}
                className="relative rounded-xl p-2 text-lovable-ink-muted transition hover:bg-lovable-surface-soft hover:text-lovable-ink"
                title="Notificações"
                aria-label={unreadCount > 0 ? `Notificações — ${unreadCount} não lidas` : "Notificações"}
              >
                <Bell size={16} aria-hidden="true" />
                {unreadCount > 0 ? (
                  <span
                    className="absolute -right-0.5 -top-0.5 flex h-4 w-4 items-center justify-center rounded-full bg-red-500 text-[10px] font-bold text-white"
                    aria-hidden="true"
                  >
                    {unreadCount > 9 ? "9+" : unreadCount}
                  </span>
                ) : null}
              </button>

              <div className="hidden rounded-xl border border-lovable-border bg-lovable-surface-soft px-3 py-2 md:block">
                <p className="text-sm font-semibold text-lovable-ink">{user?.full_name}</p>
                <p className="text-xs uppercase tracking-wide text-lovable-ink-muted">{user?.role}</p>
              </div>

              <Button variant="danger" size="sm" onClick={() => void logout()}>
                <LogOut size={14} />
                Sair
              </Button>
            </div>
          </div>
        </header>

        <main id="main-content" role="main" className="px-4 py-6 md:px-6 lg:px-8">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
