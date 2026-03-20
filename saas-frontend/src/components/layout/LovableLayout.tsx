import {
  Activity,
  Bell,
  Bot,
  Briefcase,
  CheckSquare,
  ChevronDown,
  ChevronRight,
  ClipboardList,
  Dumbbell,
  FileText,
  Globe,
  HelpCircle,
  LayoutDashboard,
  LogOut,
  Menu,
  Moon,
  ScrollText,
  Settings,
  ShieldAlert,
  Sparkles,
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
import { NavLink, Outlet, useLocation, useNavigate } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";

import { useAuth } from "../../hooks/useAuth";
import { useTheme } from "../../hooks/useTheme";
import { notificationService } from "../../services/notificationService";
import { Button, Drawer, cn } from "../ui2";

interface NavItem {
  to: string;
  label: string;
  icon: LucideIcon;
  badge?: string;
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
      { to: "/dashboard/commercial", label: "Comercial", icon: Briefcase, badge: "new" },
      { to: "/dashboard/financial", label: "Financeiro", icon: Wallet },
      { to: "/dashboard/retention", label: "Retenção", icon: ShieldAlert },
    ],
  },
  {
    label: "Gestão",
    items: [
      { to: "/members", label: "Membros", icon: UserSquare2 },
      { to: "/assessments", label: "Avaliações", icon: ClipboardList },
      { to: "/crm", label: "CRM", icon: Users, badge: "6" },
      { to: "/tasks", label: "Tarefas", icon: CheckSquare },
    ],
  },
  {
    label: "Resultados",
    items: [
      { to: "/goals", label: "Metas", icon: Target },
      { to: "/nps", label: "NPS", icon: Star },
      { to: "/reports", label: "Relatorios", icon: FileText },
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
];

function resolveActiveGroup(pathname: string): string | null {
  for (const group of navGroups) {
    if (group.items.some((item) => pathname.startsWith(item.to))) {
      return group.label;
    }
  }
  return null;
}

function resolveCurrentSection(pathname: string): string {
  if (pathname.startsWith("/settings/users")) return "Usuarios";
  if (pathname.startsWith("/settings")) return "Configuracoes";

  for (const group of navGroups) {
    const item = group.items.find((candidate) => pathname.startsWith(candidate.to));
    if (item) return item.label;
  }
  return "Dashboard";
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
      prev.includes(label) ? prev.filter((groupLabel) => groupLabel !== label) : [...prev, label],
    );
  }

  return (
    <nav className="space-y-2 px-3 pb-2">
      {navGroups.map((group) => {
        const isOpen = openGroups.includes(group.label);
        const ChevronIcon = isOpen ? ChevronDown : ChevronRight;
        return (
          <div key={group.label} className="border-b border-lovable-border/60 pb-2 last:border-b-0">
            <button
              type="button"
              onClick={() => toggleGroup(group.label)}
              title={group.label}
              className="flex w-full items-center justify-between rounded-lg px-2 py-1.5 text-[11px] font-semibold uppercase tracking-[0.18em] text-lovable-ink-muted transition hover:bg-lovable-surface-soft hover:text-lovable-ink"
            >
              {group.label}
              <ChevronIcon size={13} />
            </button>
            {isOpen ? (
              <div className="mt-1.5 space-y-1">
                {group.items.map((item) => {
                  const Icon = item.icon;
                  return (
                    <NavLink
                      key={item.to}
                      to={item.to}
                      onClick={onNavigate}
                      title={item.label}
                      className={({ isActive }) =>
                        cn(
                          "flex items-center justify-between gap-2 rounded-lg px-2.5 py-2 text-sm font-medium transition",
                          isActive
                            ? "border border-lovable-border-strong bg-lovable-surface-soft text-lovable-ink"
                            : "text-lovable-ink-muted hover:bg-lovable-surface-soft hover:text-lovable-ink",
                        )
                      }
                    >
                      <span className="flex items-center gap-2">
                        <Icon size={16} />
                        <span>{item.label}</span>
                      </span>
                      {item.badge ? (
                        <span
                          className={cn(
                            "rounded-full px-1.5 py-0.5 text-[10px] font-semibold uppercase tracking-wide",
                            item.badge === "new"
                              ? "bg-emerald-500/20 text-emerald-300"
                              : "bg-lovable-surface-soft text-lovable-ink",
                          )}
                        >
                          {item.badge}
                        </span>
                      ) : null}
                    </NavLink>
                  );
                })}
              </div>
            ) : null}
          </div>
        );
      })}
    </nav>
  );
}

export function LovableLayout() {
  const { user, logout } = useAuth();
  const { theme, toggleTheme } = useTheme();
  const { pathname } = useLocation();
  const navigate = useNavigate();
  const currentSection = resolveCurrentSection(pathname);
  const [mobileOpen, setMobileOpen] = useState(false);
  const [workspaceMenuOpen, setWorkspaceMenuOpen] = useState(false);

  const { data: notifications } = useQuery({
    queryKey: ["notifications", "unread-count"],
    queryFn: () => notificationService.listNotifications({ unread_only: false }),
    refetchInterval: 60_000,
  });

  const unreadCount = notifications?.items.filter((item) => !item.read_at).length ?? 0;
  const userEmail = user?.email ?? "owner@demo.local";

  useEffect(() => {
    setWorkspaceMenuOpen(false);
  }, [pathname]);

  return (
    <div className="relative min-h-screen bg-transparent font-body text-lovable-ink">
      <div aria-hidden="true" className="pointer-events-none fixed inset-0 -z-10 overflow-hidden">
        <div className="absolute -top-28 left-[14%] h-[380px] w-[380px] rounded-full bg-lovable-success/25 blur-[135px]" />
        <div className="absolute top-[28%] -right-20 h-[320px] w-[320px] rounded-full bg-lovable-success/18 blur-[130px]" />
        <div className="absolute -bottom-36 left-[32%] h-[420px] w-[420px] rounded-full bg-lovable-primary/14 blur-[160px]" />
      </div>

      <aside aria-label="Main navigation" className="fixed inset-y-0 left-0 z-30 hidden w-72 p-3 lg:block">
        <div className="flex h-full flex-col rounded-[24px] border border-lovable-border bg-lovable-bg/90 shadow-lovable backdrop-blur-xl">
          <div className="px-4 pt-4">
            <div className="relative">
              <button
                type="button"
                onClick={() => setWorkspaceMenuOpen((prev) => !prev)}
                className="w-full rounded-xl border border-lovable-border bg-lovable-surface/85 p-3 text-left transition hover:border-lovable-border-strong"
                aria-expanded={workspaceMenuOpen}
                aria-label="Abrir menu de usuarios"
              >
                <div className="flex items-start justify-between gap-2">
                  <div className="flex items-center gap-2">
                    <div className="flex h-8 w-8 items-center justify-center rounded-lg border border-lovable-border-strong bg-lovable-bg text-sm font-semibold text-lovable-ink">
                      <Dumbbell size={16} />
                    </div>
                    <div>
                      <p className="text-lg font-semibold text-lovable-ink">AI GYM OS</p>
                      <p className="flex items-center gap-1 text-xs text-lovable-ink-muted">
                        <span className="inline-block h-1.5 w-1.5 rounded-full bg-emerald-400" />
                        {userEmail}
                      </p>
                    </div>
                  </div>
                  <ChevronDown
                    size={14}
                    className={cn("mt-1 text-lovable-ink-muted transition-transform", workspaceMenuOpen ? "rotate-180" : "")}
                  />
                </div>
              </button>

              {workspaceMenuOpen ? (
                <div className="absolute left-0 right-0 z-20 mt-2 rounded-xl border border-lovable-border bg-lovable-surface/95 p-2 shadow-panel">
                  <button
                    type="button"
                    onClick={() => {
                      setWorkspaceMenuOpen(false);
                      navigate("/settings/users");
                    }}
                    className="flex w-full items-center gap-2 rounded-lg px-2.5 py-2 text-sm font-medium text-lovable-ink transition hover:bg-lovable-surface-soft"
                  >
                    <UserCog size={15} />
                    Usuarios
                  </button>
                  <p className="px-2.5 pb-1 text-[11px] text-lovable-ink-muted">Acesse e gerencie todos os usuarios.</p>
                </div>
              ) : null}
            </div>

            <div className="mt-4 flex items-center justify-between rounded-xl border border-lovable-border bg-lovable-surface/70 px-3 py-2">
              <p className="text-xs uppercase tracking-[0.16em] text-lovable-ink-muted">Integracoes</p>
              <div className="flex items-center gap-1">
                <span className="rounded-md bg-lovable-surface-soft p-1 text-lovable-ink-muted">
                  <Globe size={12} />
                </span>
                <span className="rounded-md bg-lovable-surface-soft p-1 text-lovable-ink-muted">
                  <Activity size={12} />
                </span>
                <span className="rounded-md bg-lovable-surface-soft p-1 text-lovable-ink-muted">
                  <Sparkles size={12} />
                </span>
              </div>
            </div>
          </div>

          <div className="mt-3 flex-1 overflow-y-auto">
            <SidebarNav />
          </div>

          <div className="space-y-3 px-4 pb-4">
            <div className="space-y-1 text-sm">
              <button
                type="button"
                onClick={() => navigate("/settings")}
                className="flex w-full items-center gap-2 rounded-lg px-2 py-1.5 text-lovable-ink-muted transition hover:bg-lovable-surface-soft hover:text-lovable-ink"
              >
                <Settings size={15} />
                Settings
              </button>
              <button
                type="button"
                onClick={() => navigate("/reports")}
                className="flex w-full items-center gap-2 rounded-lg px-2 py-1.5 text-lovable-ink-muted transition hover:bg-lovable-surface-soft hover:text-lovable-ink"
              >
                <HelpCircle size={15} />
                Help Center
              </button>
            </div>
          </div>
        </div>
      </aside>

      <Drawer open={mobileOpen} onClose={() => setMobileOpen(false)} title="AI GYM OS">
        <SidebarNav onNavigate={() => setMobileOpen(false)} />
      </Drawer>

      <div className="min-h-screen lg:ml-72">
        <header role="banner" className="sticky top-0 z-20 px-4 pt-3 md:px-6 lg:px-7">
          <div className="rounded-2xl border border-lovable-border bg-lovable-bg/92 px-4 py-3 backdrop-blur-xl">
            <div className="flex items-center justify-between gap-3">
              <div className="flex items-center gap-2">
                <Button
                  variant="ghost"
                  size="sm"
                  className="!text-lovable-ink-muted hover:!bg-lovable-surface-soft hover:!text-lovable-ink lg:hidden"
                  onClick={() => setMobileOpen(true)}
                  aria-label="Open navigation menu"
                >
                  <Menu size={16} />
                </Button>
                <div>
                  <p className="text-[11px] uppercase tracking-[0.18em] text-lovable-ink-muted">Workspace</p>
                  <h1 className="font-display text-xl font-semibold text-lovable-ink">{currentSection}</h1>
                </div>
              </div>

              <div className="flex items-center gap-2">
                <button
                  type="button"
                  onClick={toggleTheme}
                  title={theme === "dark" ? "Modo claro" : "Modo escuro"}
                  className="rounded-lg border border-lovable-border-strong bg-lovable-surface p-2 text-lovable-ink-muted transition hover:border-lovable-border-strong/90 hover:text-lovable-ink"
                >
                  {theme === "dark" ? <Sun size={15} /> : <Moon size={15} />}
                </button>

                <button
                  type="button"
                  onClick={() => navigate("/notifications")}
                  className="relative rounded-lg border border-lovable-border-strong bg-lovable-surface p-2 text-lovable-ink-muted transition hover:border-lovable-border-strong/90 hover:text-lovable-ink"
                  title="Notifications"
                  aria-label={unreadCount > 0 ? `Notifications ${unreadCount} unread` : "Notifications"}
                >
                  <Bell size={15} aria-hidden="true" />
                  {unreadCount > 0 ? (
                    <span
                      className="absolute -right-1 -top-1 flex h-4 w-4 items-center justify-center rounded-full bg-rose-500 text-[10px] font-bold text-white"
                      aria-hidden="true"
                    >
                      {unreadCount > 9 ? "9+" : unreadCount}
                    </span>
                  ) : null}
                </button>

                <div className="hidden items-center gap-2 rounded-lg border border-lovable-border-strong bg-lovable-surface px-3 py-1.5 md:flex">
                  <div className="text-right">
                    <p className="text-sm font-semibold text-lovable-ink">{user?.full_name ?? "Owner"}</p>
                    <p className="text-[11px] uppercase tracking-wider text-lovable-ink-muted">{user?.role ?? "owner"}</p>
                  </div>
                </div>

                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => void logout()}
                  title="Sair"
                  aria-label="Sair"
                  className="!px-2 !text-lovable-ink-muted hover:!bg-lovable-surface-soft hover:!text-lovable-ink"
                >
                  <LogOut size={14} />
                </Button>
              </div>
            </div>
          </div>
        </header>

        <main id="main-content" role="main" className="px-4 py-5 md:px-6 lg:px-7">
          <div className="mx-auto w-full max-w-[1560px]">
            <Outlet />
          </div>
        </main>
      </div>
    </div>
  );
}
