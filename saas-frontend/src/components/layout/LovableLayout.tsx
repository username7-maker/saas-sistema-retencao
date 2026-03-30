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
  Search,
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
import { useEffect, useMemo, useState } from "react";
import { NavLink, Outlet, useLocation, useNavigate } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";

import { useAuth } from "../../hooks/useAuth";
import { useTheme } from "../../hooks/useTheme";
import { notificationService } from "../../services/notificationService";
import { canAccessRoute, canManageUsers } from "../../utils/roleAccess";
import { Button, Drawer, Input, cn } from "../ui2";
import type { RouteAccessKey } from "../../utils/roleAccess";

interface NavItem {
  to: string;
  label: string;
  icon: LucideIcon;
  route: RouteAccessKey;
  badge?: string;
}

interface NavGroup {
  label: string;
  items: NavItem[];
}

interface HeaderSearchConfig {
  param: string;
  placeholder: string;
}

const navGroups: NavGroup[] = [
  {
    label: "Dashboards",
    items: [
      { to: "/dashboard/executive", label: "Executivo", icon: LayoutDashboard, route: "dashboardExecutive" },
      { to: "/dashboard/operational", label: "Operacional", icon: Activity, route: "dashboardOperational" },
      { to: "/dashboard/commercial", label: "Comercial", icon: Briefcase, route: "dashboardCommercial", badge: "new" },
      { to: "/dashboard/financial", label: "Financeiro", icon: Wallet, route: "dashboardFinancial" },
      { to: "/dashboard/retention", label: "Retencao", icon: ShieldAlert, route: "dashboardRetention" },
    ],
  },
  {
    label: "Gestao",
    items: [
      { to: "/members", label: "Membros", icon: UserSquare2, route: "members" },
      { to: "/assessments", label: "Avaliacoes", icon: ClipboardList, route: "assessments" },
      { to: "/crm", label: "CRM", icon: Users, route: "crm", badge: "6" },
      { to: "/tasks", label: "Tarefas", icon: CheckSquare, route: "tasks" },
    ],
  },
  {
    label: "Resultados",
    items: [
      { to: "/goals", label: "Metas", icon: Target, route: "goals" },
      { to: "/nps", label: "NPS", icon: Star, route: "nps" },
      { to: "/reports", label: "Relatorios", icon: FileText, route: "reports" },
    ],
  },
  {
    label: "Sistema",
    items: [
      { to: "/automations", label: "Automacoes", icon: Bot, route: "automations" },
      { to: "/imports", label: "Importacoes", icon: Upload, route: "imports" },
      { to: "/audit", label: "Auditoria", icon: ScrollText, route: "audit" },
    ],
  },
];

const trainerNavGroups: NavGroup[] = [
  {
    label: "Treino",
    items: [{ to: "/assessments", label: "Avaliacoes", icon: ClipboardList, route: "assessments" }],
  },
];

function resolveHeaderSearchConfig(pathname: string): HeaderSearchConfig | null {
  if (pathname.startsWith("/dashboard/retention")) {
    return { param: "search", placeholder: "Buscar alertas, aluno ou plano..." };
  }
  if (pathname.startsWith("/tasks")) {
    return { param: "search", placeholder: "Buscar tarefas, aluno ou lead..." };
  }
  if (pathname === "/members") {
    return { param: "search", placeholder: "Buscar nome, email, matricula, telefone ou CPF..." };
  }
  if (pathname === "/assessments") {
    return { param: "search", placeholder: "Buscar aluno, plano, telefone ou CPF..." };
  }
  return null;
}

function resolveActiveGroup(pathname: string, groups: NavGroup[] = navGroups): string | null {
  for (const group of groups) {
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
  const { user } = useAuth();
  const { pathname } = useLocation();
  const groups = useMemo(() => {
    if (user?.role === "trainer") {
      return trainerNavGroups;
    }
    return navGroups
      .map((group) => ({
        ...group,
        items: group.items.filter((item) => canAccessRoute(user?.role, item.route)),
      }))
      .filter((group) => group.items.length > 0);
  }, [user?.role]);
  const activeGroup = resolveActiveGroup(pathname, groups);
  const [openGroups, setOpenGroups] = useState<string[]>(activeGroup ? [activeGroup] : [groups[0]?.label ?? ""]);

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
    <nav className="space-y-4 px-3 pb-2">
      {groups.map((group) => {
        const isOpen = openGroups.includes(group.label);
        const ChevronIcon = isOpen ? ChevronDown : ChevronRight;

        return (
          <div key={group.label} className="space-y-1.5">
            <button
              type="button"
              onClick={() => toggleGroup(group.label)}
              title={group.label}
              className="flex w-full items-center justify-between rounded-xl px-3 py-2 text-[11px] font-semibold uppercase tracking-[0.26em] text-lovable-ink-muted transition hover:bg-lovable-surface-soft/55 hover:text-lovable-ink"
            >
              <span>{group.label}</span>
              <ChevronIcon size={13} />
            </button>

            {isOpen ? (
              <div className="space-y-1">
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
                          "group flex items-center justify-between gap-3 rounded-2xl px-3 py-2.5 text-sm font-medium transition-all duration-200",
                          isActive
                            ? "border border-[hsl(var(--lovable-primary)/0.34)] bg-[linear-gradient(135deg,hsl(var(--lovable-primary)/0.24),hsl(var(--lovable-info)/0.18))] text-lovable-ink shadow-[0_16px_40px_-24px_hsl(var(--lovable-primary)/0.95)]"
                            : "border border-transparent text-lovable-ink-muted hover:border-lovable-border/50 hover:bg-lovable-surface-soft/62 hover:text-lovable-ink",
                        )
                      }
                    >
                      <span className="flex min-w-0 items-center gap-3">
                        <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-xl border border-lovable-border/60 bg-lovable-surface-soft/72 text-lovable-ink-muted transition group-hover:text-lovable-ink">
                          <Icon size={15} />
                        </span>
                        <span className="truncate">{item.label}</span>
                      </span>

                      {item.badge ? (
                        <span
                          className={cn(
                            "rounded-full px-2 py-0.5 text-[10px] font-semibold uppercase tracking-[0.18em]",
                            item.badge === "new"
                              ? "bg-[hsl(var(--lovable-success)/0.18)] text-[hsl(var(--lovable-success))]"
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
  const location = useLocation();
  const { pathname } = location;
  const navigate = useNavigate();
  const currentSection = resolveCurrentSection(pathname);
  const searchConfig = useMemo(() => resolveHeaderSearchConfig(pathname), [pathname]);
  const [mobileOpen, setMobileOpen] = useState(false);
  const [workspaceMenuOpen, setWorkspaceMenuOpen] = useState(false);
  const [headerSearch, setHeaderSearch] = useState("");
  const canOpenUserDirectory = canManageUsers(user?.role);
  const canViewNotifications = canAccessRoute(user?.role, "notifications");
  const profileTarget = canOpenUserDirectory ? "/settings/users" : "/settings";
  const showHelpCenter = canAccessRoute(user?.role, "reports");

  const { data: notifications } = useQuery({
    queryKey: ["notifications", "unread-count"],
    queryFn: () => notificationService.listNotifications({ unread_only: false }),
    refetchInterval: 60_000,
    enabled: canViewNotifications,
  });

  const unreadCount = notifications?.items.filter((item) => !item.read_at).length ?? 0;
  const userEmail = user?.email ?? "owner@demo.local";
  const userInitials = useMemo(() => {
    const source = user?.full_name ?? "Owner";
    return source
      .split(/\s+/)
      .filter(Boolean)
      .slice(0, 2)
      .map((part) => part.charAt(0).toUpperCase())
      .join("");
  }, [user?.full_name]);

  useEffect(() => {
    setWorkspaceMenuOpen(false);
  }, [pathname]);

  useEffect(() => {
    if (!searchConfig) {
      setHeaderSearch("");
      return;
    }
    const params = new URLSearchParams(location.search);
    const nextValue = params.get(searchConfig.param) ?? "";
    setHeaderSearch((previous) => (previous === nextValue ? previous : nextValue));
  }, [searchConfig, location.search]);

  useEffect(() => {
    if (!searchConfig) return;

    const params = new URLSearchParams(location.search);
    const currentValue = params.get(searchConfig.param) ?? "";
    const trimmedValue = headerSearch.trim();

    if (trimmedValue === currentValue) return;

    const timer = window.setTimeout(() => {
      const nextParams = new URLSearchParams(location.search);
      if (trimmedValue) {
        nextParams.set(searchConfig.param, trimmedValue);
      } else {
        nextParams.delete(searchConfig.param);
      }
      const nextSearch = nextParams.toString();
      navigate(
        {
          pathname,
          search: nextSearch ? `?${nextSearch}` : "",
        },
        { replace: true },
      );
    }, 250);

    return () => window.clearTimeout(timer);
  }, [headerSearch, location.search, navigate, pathname, searchConfig]);

  return (
    <div className="relative min-h-screen bg-lovable-bg font-body text-lovable-ink">
      <div aria-hidden="true" className="pointer-events-none fixed inset-0 -z-10 overflow-hidden">
        <div className="absolute -left-24 -top-20 h-[420px] w-[420px] rounded-full bg-[hsl(var(--lovable-primary)/0.22)] blur-[150px]" />
        <div className="absolute right-[-140px] top-[10%] h-[360px] w-[360px] rounded-full bg-[hsl(var(--lovable-info)/0.16)] blur-[150px]" />
        <div className="absolute bottom-[-180px] left-[28%] h-[440px] w-[440px] rounded-full bg-[hsl(var(--lovable-success)/0.09)] blur-[170px]" />
      </div>

      <aside aria-label="Main navigation" className="fixed inset-y-0 left-0 z-30 hidden w-72 p-3 lg:block">
        <div className="flex h-full flex-col rounded-[30px] border border-lovable-border/70 bg-[hsl(var(--lovable-sidebar)/0.94)] shadow-panel backdrop-blur-2xl">
          <div className="px-4 pt-4">
            <div className="relative">
              <button
                type="button"
                onClick={() => {
                  if (canOpenUserDirectory) {
                    setWorkspaceMenuOpen((prev) => !prev);
                    return;
                  }
                  navigate("/settings");
                }}
                className="w-full rounded-2xl border border-lovable-border/70 bg-lovable-surface/68 p-3.5 text-left shadow-[inset_0_1px_0_hsl(0_0%_100%/0.04)] transition hover:border-lovable-border-strong/70 hover:bg-lovable-surface/80"
                aria-expanded={canOpenUserDirectory ? workspaceMenuOpen : undefined}
                aria-label={canOpenUserDirectory ? "Abrir menu de usuarios" : "Abrir configuracoes"}
              >
                <div className="flex items-start justify-between gap-3">
                  <div className="flex min-w-0 items-center gap-3">
                    <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-2xl bg-[linear-gradient(135deg,hsl(var(--lovable-primary)),hsl(var(--lovable-info)))] text-white shadow-[0_18px_40px_-20px_hsl(var(--lovable-primary)/0.95)]">
                      <Dumbbell size={18} />
                    </div>
                    <div className="min-w-0">
                      <p className="truncate font-heading text-xl font-bold tracking-tight text-lovable-ink">AI GYM OS</p>
                      <p className="mt-0.5 flex items-center gap-1.5 text-xs uppercase tracking-[0.18em] text-lovable-ink-muted">
                        <span className="inline-block h-1.5 w-1.5 rounded-full bg-[hsl(var(--lovable-success))]" />
                        Retencao inteligente
                      </p>
                      <p className="mt-1 truncate text-xs text-lovable-ink-muted">{userEmail}</p>
                    </div>
                  </div>
                  {canOpenUserDirectory ? (
                    <ChevronDown
                      size={14}
                      className={cn("mt-1 shrink-0 text-lovable-ink-muted transition-transform", workspaceMenuOpen ? "rotate-180" : "")}
                    />
                  ) : (
                    <Settings size={14} className="mt-1 shrink-0 text-lovable-ink-muted" />
                  )}
                </div>
              </button>

              {canOpenUserDirectory && workspaceMenuOpen ? (
                <div className="absolute left-0 right-0 z-20 mt-2 rounded-2xl border border-lovable-border/70 bg-lovable-surface/96 p-2 shadow-panel backdrop-blur-xl">
                  <button
                    type="button"
                    onClick={() => {
                      setWorkspaceMenuOpen(false);
                      navigate("/settings/users");
                    }}
                    className="flex w-full items-center gap-2 rounded-xl px-3 py-2 text-sm font-medium text-lovable-ink transition hover:bg-lovable-surface-soft"
                  >
                    <UserCog size={15} />
                    Usuarios
                  </button>
                  <p className="px-3 pb-1 text-[11px] uppercase tracking-[0.18em] text-lovable-ink-muted">
                    Gerencie perfis e acessos
                  </p>
                </div>
              ) : null}
            </div>

            <div className="mt-4 flex items-center justify-between rounded-2xl border border-lovable-border/60 bg-lovable-surface/55 px-3 py-2.5">
              <p className="text-[11px] font-semibold uppercase tracking-[0.24em] text-lovable-ink-muted">Integracoes</p>
              <div className="flex items-center gap-1.5">
                <span className="rounded-lg border border-lovable-border/60 bg-lovable-surface-soft/72 p-1.5 text-lovable-ink-muted">
                  <Globe size={12} />
                </span>
                <span className="rounded-lg border border-lovable-border/60 bg-lovable-surface-soft/72 p-1.5 text-lovable-ink-muted">
                  <Activity size={12} />
                </span>
                <span className="rounded-lg border border-lovable-border/60 bg-lovable-surface-soft/72 p-1.5 text-[hsl(var(--lovable-primary))]">
                  <Sparkles size={12} />
                </span>
              </div>
            </div>
          </div>

          <div className="mt-4 flex-1 overflow-y-auto">
            <SidebarNav />
          </div>

          <div className="space-y-2 px-4 pb-4 pt-2">
            <button
              type="button"
              onClick={() => navigate("/settings")}
              className="flex w-full items-center gap-3 rounded-2xl border border-transparent px-3 py-2.5 text-sm font-medium text-lovable-ink-muted transition hover:border-lovable-border/50 hover:bg-lovable-surface-soft/62 hover:text-lovable-ink"
            >
              <Settings size={16} />
              Settings
            </button>
            {showHelpCenter ? (
              <button
                type="button"
                onClick={() => navigate("/reports")}
                className="flex w-full items-center gap-3 rounded-2xl border border-transparent px-3 py-2.5 text-sm font-medium text-lovable-ink-muted transition hover:border-lovable-border/50 hover:bg-lovable-surface-soft/62 hover:text-lovable-ink"
              >
                <HelpCircle size={16} />
                Help Center
              </button>
            ) : null}
          </div>
        </div>
      </aside>

      <Drawer open={mobileOpen} onClose={() => setMobileOpen(false)} title="AI GYM OS">
        <SidebarNav onNavigate={() => setMobileOpen(false)} />
      </Drawer>

      <div className="min-h-screen lg:ml-72">
        <header role="banner" className="sticky top-0 z-20 px-4 pt-3 md:px-6 lg:px-7">
          <div className="rounded-[24px] border border-lovable-border/70 bg-[hsl(var(--lovable-topbar)/0.92)] px-4 py-3 shadow-panel backdrop-blur-2xl">
            <div className="flex items-center justify-between gap-3">
              <div className="flex min-w-0 items-center gap-3">
                <Button
                  variant="ghost"
                  size="sm"
                  className="!rounded-xl !border !border-lovable-border/50 !bg-lovable-surface/60 !px-2.5 !text-lovable-ink-muted hover:!border-lovable-border-strong/60 hover:!bg-lovable-surface-soft hover:!text-lovable-ink lg:hidden"
                  onClick={() => setMobileOpen(true)}
                  aria-label="Open navigation menu"
                >
                  <Menu size={16} />
                </Button>

                <div className="min-w-0">
                  <p className="text-[11px] font-semibold uppercase tracking-[0.26em] text-lovable-ink-muted">Workspace</p>
                  <h1 className="truncate font-heading text-2xl font-bold tracking-tight text-lovable-ink">{currentSection}</h1>
                </div>
              </div>

              <div className="hidden w-full max-w-md items-center lg:flex">
                <div className="relative w-full">
                  <Search
                    size={16}
                    className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-lovable-ink-muted"
                  />
                  <Input
                    value={headerSearch}
                    onChange={(event) => setHeaderSearch(event.target.value)}
                    placeholder={searchConfig?.placeholder ?? "Busca contextual indisponivel nesta tela"}
                    disabled={!searchConfig}
                    className="h-11 rounded-2xl border-lovable-border/60 bg-lovable-surface/62 pl-10 shadow-none"
                  />
                </div>
              </div>

              <div className="flex shrink-0 items-center gap-2">
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={toggleTheme}
                  title={theme === "dark" ? "Modo claro" : "Modo escuro"}
                  className="!rounded-xl !border !border-lovable-border/60 !bg-lovable-surface/62 !px-2.5 !text-lovable-ink-muted hover:!border-lovable-border-strong/60 hover:!bg-lovable-surface-soft hover:!text-lovable-ink"
                >
                  {theme === "dark" ? <Sun size={15} /> : <Moon size={15} />}
                </Button>

                {canViewNotifications ? (
                  <button
                    type="button"
                    onClick={() => navigate("/notifications")}
                    className="relative rounded-xl border border-lovable-border/60 bg-lovable-surface/62 p-2.5 text-lovable-ink-muted transition hover:border-lovable-border-strong/60 hover:bg-lovable-surface-soft hover:text-lovable-ink"
                    title="Notifications"
                    aria-label={unreadCount > 0 ? `Notifications ${unreadCount} unread` : "Notifications"}
                  >
                    <Bell size={15} aria-hidden="true" />
                    {unreadCount > 0 ? (
                      <span
                        className="absolute -right-1 -top-1 flex h-4 w-4 items-center justify-center rounded-full bg-[hsl(var(--lovable-danger))] text-[10px] font-bold text-white"
                        aria-hidden="true"
                      >
                        {unreadCount > 9 ? "9+" : unreadCount}
                      </span>
                    ) : null}
                  </button>
                ) : null}

                <button
                  type="button"
                  onClick={() => navigate(profileTarget)}
                  className="hidden items-center gap-3 rounded-2xl border border-lovable-border/60 bg-lovable-surface/62 px-3 py-1.5 text-left transition hover:border-lovable-border-strong/60 hover:bg-lovable-surface-soft md:flex"
                >
                  <div className="flex h-10 w-10 items-center justify-center rounded-2xl bg-[linear-gradient(135deg,hsl(var(--lovable-primary)/0.9),hsl(var(--lovable-info)/0.9))] text-sm font-bold text-white shadow-[0_12px_30px_-18px_hsl(var(--lovable-primary)/0.95)]">
                    {userInitials}
                  </div>
                  <div>
                    <p className="text-sm font-semibold text-lovable-ink">{user?.full_name ?? "Owner"}</p>
                    <p className="text-[11px] uppercase tracking-[0.18em] text-lovable-ink-muted">{user?.role ?? "owner"}</p>
                  </div>
                </button>

                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => void logout()}
                  title="Sair"
                  aria-label="Sair"
                  className="!rounded-xl !border !border-lovable-border/60 !bg-lovable-surface/62 !px-2.5 !text-lovable-ink-muted hover:!border-lovable-border-strong/60 hover:!bg-lovable-surface-soft hover:!text-lovable-ink"
                >
                  <LogOut size={15} />
                </Button>
              </div>
            </div>
          </div>
        </header>

        <main id="main-content" role="main" className="px-4 py-5 md:px-6 lg:px-7">
          <div className="mx-auto w-full max-w-[1600px]">
            <Outlet />
          </div>
        </main>
      </div>
    </div>
  );
}
