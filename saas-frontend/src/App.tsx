import { lazy, Suspense } from "react";
import { Navigate, Route, Routes } from "react-router-dom";

import { ErrorBoundary } from "./components/common/ErrorBoundary";
import { LoadingPanel } from "./components/common/LoadingPanel";
import { ProtectedRoute } from "./components/common/ProtectedRoute";
import { LovableLayout } from "./components/layout/LovableLayout";
import { useAuth } from "./hooks/useAuth";
import { LoginPage } from "./pages/auth/LoginPage";
import { ResetPasswordPage } from "./pages/auth/ResetPasswordPage";
import { DiagnosticoPage } from "./pages/public/DiagnosticoPage";
import { ROUTE_ACCESS, USER_ADMIN_ROLES, getDefaultRouteForRole } from "./utils/roleAccess";
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
      <Route path="/reset-password" element={<ResetPasswordPage />} />

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
            <GuardedLazyRoute allowedRoles={[...ROUTE_ACCESS.members]}>
              <MembersPage />
            </GuardedLazyRoute>
          }
        />
        <Route
          path="/dashboard/executive"
          element={
            <GuardedLazyRoute allowedRoles={[...ROUTE_ACCESS.dashboardExecutive]}>
              <DashboardLovable />
            </GuardedLazyRoute>
          }
        />
        <Route
          path="/dashboard/operational"
          element={
            <GuardedLazyRoute allowedRoles={[...ROUTE_ACCESS.dashboardOperational]}>
              <OperationalDashboardPage />
            </GuardedLazyRoute>
          }
        />
        <Route
          path="/dashboard/commercial"
          element={
            <GuardedLazyRoute allowedRoles={[...ROUTE_ACCESS.dashboardCommercial]}>
              <CommercialDashboardPage />
            </GuardedLazyRoute>
          }
        />
        <Route
          path="/dashboard/financial"
          element={
            <GuardedLazyRoute allowedRoles={[...ROUTE_ACCESS.dashboardFinancial]}>
              <FinancialDashboardPage />
            </GuardedLazyRoute>
          }
        />
        <Route
          path="/dashboard/retention"
          element={
            <GuardedLazyRoute allowedRoles={[...ROUTE_ACCESS.dashboardRetention]}>
              <RetentionDashboardPage />
            </GuardedLazyRoute>
          }
        />
        <Route
          path="/crm"
          element={
            <GuardedLazyRoute allowedRoles={[...ROUTE_ACCESS.crm]}>
              <CrmPage />
            </GuardedLazyRoute>
          }
        />
        <Route
          path="/tasks"
          element={
            <GuardedLazyRoute allowedRoles={[...ROUTE_ACCESS.tasks]}>
              <TasksPage />
            </GuardedLazyRoute>
          }
        />
        <Route
          path="/goals"
          element={
            <GuardedLazyRoute allowedRoles={[...ROUTE_ACCESS.goals]}>
              <GoalsPage />
            </GuardedLazyRoute>
          }
        />
        <Route
          path="/reports"
          element={
            <GuardedLazyRoute allowedRoles={[...ROUTE_ACCESS.reports]}>
              <ReportsPage />
            </GuardedLazyRoute>
          }
        />
        <Route
          path="/assessments"
          element={
            <GuardedLazyRoute allowedRoles={[...ROUTE_ACCESS.assessments]}>
              <AssessmentsPage />
            </GuardedLazyRoute>
          }
        />
        <Route
          path="/assessments/members/:memberId"
          element={
            <GuardedLazyRoute allowedRoles={[...ROUTE_ACCESS.assessmentContext]}>
              <MemberProfile360Page />
            </GuardedLazyRoute>
          }
        />
        <Route
          path="/assessments/new/:memberId"
          element={
            <GuardedLazyRoute allowedRoles={[...ROUTE_ACCESS.assessmentRegistration]}>
              <NewAssessmentPage />
            </GuardedLazyRoute>
          }
        />
        <Route
          path="/notifications"
          element={
            <GuardedLazyRoute allowedRoles={[...ROUTE_ACCESS.notifications]}>
              <NotificationsPage />
            </GuardedLazyRoute>
          }
        />
        <Route
          path="/automations"
          element={
            <GuardedLazyRoute allowedRoles={[...ROUTE_ACCESS.automations]}>
              <AutomationsPage />
            </GuardedLazyRoute>
          }
        />
        <Route
          path="/imports"
          element={
            <GuardedLazyRoute allowedRoles={[...ROUTE_ACCESS.imports]}>
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
            <GuardedLazyRoute allowedRoles={[...ROUTE_ACCESS.nps]}>
              <NpsPage />
            </GuardedLazyRoute>
          }
        />
        <Route
          path="/audit"
          element={
            <GuardedLazyRoute allowedRoles={[...ROUTE_ACCESS.audit]}>
              <AuditPage />
            </GuardedLazyRoute>
          }
        />
        <Route
          path="/vendas/briefing/:leadId"
          element={
            <GuardedLazyRoute allowedRoles={[...ROUTE_ACCESS.sales]}>
              <SalesBriefingPage />
            </GuardedLazyRoute>
          }
        />
        <Route
          path="/vendas/script/:leadId"
          element={
            <GuardedLazyRoute allowedRoles={[...ROUTE_ACCESS.sales]}>
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
