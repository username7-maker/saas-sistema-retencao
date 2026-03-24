import { lazy, Suspense } from "react";
import { Navigate, Route, Routes } from "react-router-dom";

import { ErrorBoundary } from "./components/common/ErrorBoundary";
import { LoadingPanel } from "./components/common/LoadingPanel";
import { ProtectedRoute } from "./components/common/ProtectedRoute";
import { LovableLayout } from "./components/layout/LovableLayout";
import { useAuth } from "./hooks/useAuth";
import { LoginPage } from "./pages/auth/LoginPage";
import { DiagnosticoPage } from "./pages/public/DiagnosticoPage";
import { NON_TRAINER_ROLES, USER_ADMIN_ROLES, getDefaultRouteForRole } from "./utils/roleAccess";
import type { Role } from "./types";

const MembersPage = lazy(() => import("./pages/members/MembersPage").then((m) => ({ default: m.MembersPage })));
const DashboardLovable = lazy(() => import("./pages/dashboard/DashboardLovable").then((m) => ({ default: m.DashboardLovable })));
const OperationalDashboardPage = lazy(() => import("./pages/dashboard/OperationalDashboardPage").then((m) => ({ default: m.OperationalDashboardPage })));
const CommercialDashboardPage = lazy(() => import("./pages/dashboard/CommercialDashboardPage").then((m) => ({ default: m.CommercialDashboardPage })));
const FinancialDashboardPage = lazy(() => import("./pages/dashboard/FinancialDashboardPage").then((m) => ({ default: m.FinancialDashboardPage })));
const RetentionDashboardPage = lazy(() => import("./pages/dashboard/RetentionDashboardPage").then((m) => ({ default: m.RetentionDashboardPage })));
const CrmPage = lazy(() => import("./pages/crm/CrmPage").then((m) => ({ default: m.CrmPage })));
const TasksPage = lazy(() => import("./pages/tasks/TasksPage").then((m) => ({ default: m.TasksPage })));
const NotificationsPage = lazy(() => import("./pages/notifications/NotificationsPage").then((m) => ({ default: m.NotificationsPage })));
const AutomationsPage = lazy(() => import("./pages/automations/AutomationsPage").then((m) => ({ default: m.AutomationsPage })));
const GoalsPage = lazy(() => import("./pages/goals/GoalsPage").then((m) => ({ default: m.GoalsPage })));
const ReportsPage = lazy(() => import("./pages/reports/ReportsPage"));
const AssessmentsPage = lazy(() => import("./pages/assessments/AssessmentsPage").then((m) => ({ default: m.AssessmentsPage })));
const MemberProfile360Page = lazy(() => import("./pages/assessments/MemberProfile360Page").then((m) => ({ default: m.MemberProfile360Page })));
const NewAssessmentPage = lazy(() => import("./pages/assessments/NewAssessmentPage").then((m) => ({ default: m.NewAssessmentPage })));
const ImportsPage = lazy(() => import("./pages/imports/ImportsPage").then((m) => ({ default: m.ImportsPage })));
const SettingsPage = lazy(() => import("./pages/settings/SettingsPage").then((m) => ({ default: m.SettingsPage })));
const UsersPage = lazy(() => import("./pages/settings/UsersPage").then((m) => ({ default: m.UsersPage })));
const NpsPage = lazy(() => import("./pages/nps/NpsPage").then((m) => ({ default: m.NpsPage })));
const AuditPage = lazy(() => import("./pages/audit/AuditPage").then((m) => ({ default: m.AuditPage })));
const SalesBriefingPage = lazy(() => import("./pages/sales/SalesBriefingPage").then((m) => ({ default: m.SalesBriefingPage })));
const CallScriptPage = lazy(() => import("./pages/sales/CallScriptPage").then((m) => ({ default: m.CallScriptPage })));

function LazyWrapper({ children }: { children: React.ReactNode }) {
  return (
    <ErrorBoundary>
      <Suspense fallback={<LoadingPanel text="Carregando modulo..." />}>{children}</Suspense>
    </ErrorBoundary>
  );
}

function GuardedLazyRoute({
  children,
  allowedRoles,
}: {
  children: React.ReactNode;
  allowedRoles?: Role[];
}) {
  return (
    <ProtectedRoute allowedRoles={allowedRoles}>
      <LazyWrapper>{children}</LazyWrapper>
    </ProtectedRoute>
  );
}

function RoleHomeRedirect() {
  const { user } = useAuth();
  return <Navigate to={getDefaultRouteForRole(user?.role)} replace />;
}

export default function App() {
  return (
    <Routes>
      <Route path="/diagnostico" element={<DiagnosticoPage />} />
      <Route path="/login" element={<LoginPage />} />

      <Route
        element={
          <ProtectedRoute>
            <LovableLayout />
          </ProtectedRoute>
        }
      >
        <Route
          path="/members"
          element={
            <GuardedLazyRoute allowedRoles={NON_TRAINER_ROLES}>
              <MembersPage />
            </GuardedLazyRoute>
          }
        />
        <Route
          path="/dashboard/executive"
          element={
            <GuardedLazyRoute allowedRoles={NON_TRAINER_ROLES}>
              <DashboardLovable />
            </GuardedLazyRoute>
          }
        />
        <Route
          path="/dashboard/operational"
          element={
            <GuardedLazyRoute allowedRoles={NON_TRAINER_ROLES}>
              <OperationalDashboardPage />
            </GuardedLazyRoute>
          }
        />
        <Route
          path="/dashboard/commercial"
          element={
            <GuardedLazyRoute allowedRoles={NON_TRAINER_ROLES}>
              <CommercialDashboardPage />
            </GuardedLazyRoute>
          }
        />
        <Route
          path="/dashboard/financial"
          element={
            <GuardedLazyRoute allowedRoles={NON_TRAINER_ROLES}>
              <FinancialDashboardPage />
            </GuardedLazyRoute>
          }
        />
        <Route
          path="/dashboard/retention"
          element={
            <GuardedLazyRoute allowedRoles={NON_TRAINER_ROLES}>
              <RetentionDashboardPage />
            </GuardedLazyRoute>
          }
        />
        <Route
          path="/crm"
          element={
            <GuardedLazyRoute allowedRoles={NON_TRAINER_ROLES}>
              <CrmPage />
            </GuardedLazyRoute>
          }
        />
        <Route
          path="/tasks"
          element={
            <GuardedLazyRoute allowedRoles={NON_TRAINER_ROLES}>
              <TasksPage />
            </GuardedLazyRoute>
          }
        />
        <Route
          path="/goals"
          element={
            <GuardedLazyRoute allowedRoles={NON_TRAINER_ROLES}>
              <GoalsPage />
            </GuardedLazyRoute>
          }
        />
        <Route
          path="/reports"
          element={
            <GuardedLazyRoute allowedRoles={NON_TRAINER_ROLES}>
              <ReportsPage />
            </GuardedLazyRoute>
          }
        />
        <Route
          path="/assessments"
          element={
            <GuardedLazyRoute>
              <AssessmentsPage />
            </GuardedLazyRoute>
          }
        />
        <Route
          path="/assessments/members/:memberId"
          element={
            <GuardedLazyRoute>
              <MemberProfile360Page />
            </GuardedLazyRoute>
          }
        />
        <Route
          path="/assessments/new/:memberId"
          element={
            <GuardedLazyRoute>
              <NewAssessmentPage />
            </GuardedLazyRoute>
          }
        />
        <Route
          path="/notifications"
          element={
            <GuardedLazyRoute allowedRoles={NON_TRAINER_ROLES}>
              <NotificationsPage />
            </GuardedLazyRoute>
          }
        />
        <Route
          path="/automations"
          element={
            <GuardedLazyRoute allowedRoles={NON_TRAINER_ROLES}>
              <AutomationsPage />
            </GuardedLazyRoute>
          }
        />
        <Route
          path="/imports"
          element={
            <GuardedLazyRoute allowedRoles={NON_TRAINER_ROLES}>
              <ImportsPage />
            </GuardedLazyRoute>
          }
        />
        <Route
          path="/settings"
          element={
            <GuardedLazyRoute>
              <SettingsPage />
            </GuardedLazyRoute>
          }
        />
        <Route
          path="/settings/users"
          element={
            <GuardedLazyRoute allowedRoles={USER_ADMIN_ROLES}>
              <UsersPage />
            </GuardedLazyRoute>
          }
        />
        <Route
          path="/nps"
          element={
            <GuardedLazyRoute allowedRoles={NON_TRAINER_ROLES}>
              <NpsPage />
            </GuardedLazyRoute>
          }
        />
        <Route
          path="/audit"
          element={
            <GuardedLazyRoute allowedRoles={NON_TRAINER_ROLES}>
              <AuditPage />
            </GuardedLazyRoute>
          }
        />
        <Route
          path="/vendas/briefing/:leadId"
          element={
            <GuardedLazyRoute allowedRoles={NON_TRAINER_ROLES}>
              <SalesBriefingPage />
            </GuardedLazyRoute>
          }
        />
        <Route
          path="/vendas/script/:leadId"
          element={
            <GuardedLazyRoute allowedRoles={NON_TRAINER_ROLES}>
              <CallScriptPage />
            </GuardedLazyRoute>
          }
        />
      </Route>

      <Route
        path="*"
        element={
          <ProtectedRoute>
            <RoleHomeRedirect />
          </ProtectedRoute>
        }
      />
    </Routes>
  );
}
