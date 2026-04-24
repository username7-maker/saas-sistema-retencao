import { lazy, Suspense } from "react";
import { Navigate, Route, Routes } from "react-router-dom";

import { ErrorBoundary } from "./components/common/ErrorBoundary";
import { LoadingPanel } from "./components/common/LoadingPanel";
import { ProtectedRoute } from "./components/common/ProtectedRoute";
import { LovableLayout } from "./components/layout/LovableLayout";
import { LoginPage } from "./pages/auth/LoginPage";
import { DiagnosticoPage } from "./pages/public/DiagnosticoPage";
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

const ALL_STAFF_ROLES: Role[] = ["owner", "manager", "receptionist", "salesperson", "trainer"];
const MANAGEMENT_ROLES: Role[] = ["owner", "manager"];
const FRONT_DESK_ROLES: Role[] = ["owner", "manager", "receptionist"];
const SALES_ROLES: Role[] = ["owner", "manager", "salesperson"];
const MEMBER_READ_ROLES: Role[] = ALL_STAFF_ROLES;
const ASSESSMENT_WRITE_ROLES: Role[] = ["owner", "manager", "trainer"];

function RoleGate({ allowedRoles, children }: { allowedRoles: Role[]; children: React.ReactNode }) {
  return <ProtectedRoute allowedRoles={allowedRoles}>{children}</ProtectedRoute>;
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
            <RoleGate allowedRoles={MEMBER_READ_ROLES}>
              <LazyWrapper>
                <MembersPage />
              </LazyWrapper>
            </RoleGate>
          }
        />
        <Route
          path="/dashboard/executive"
          element={
            <RoleGate allowedRoles={MANAGEMENT_ROLES}>
              <LazyWrapper>
                <DashboardLovable />
              </LazyWrapper>
            </RoleGate>
          }
        />
        <Route
          path="/dashboard/operational"
          element={
            <RoleGate allowedRoles={FRONT_DESK_ROLES}>
              <LazyWrapper>
                <OperationalDashboardPage />
              </LazyWrapper>
            </RoleGate>
          }
        />
        <Route
          path="/dashboard/commercial"
          element={
            <RoleGate allowedRoles={SALES_ROLES}>
              <LazyWrapper>
                <CommercialDashboardPage />
              </LazyWrapper>
            </RoleGate>
          }
        />
        <Route
          path="/dashboard/financial"
          element={
            <RoleGate allowedRoles={MANAGEMENT_ROLES}>
              <LazyWrapper>
                <FinancialDashboardPage />
              </LazyWrapper>
            </RoleGate>
          }
        />
        <Route
          path="/dashboard/retention"
          element={
            <RoleGate allowedRoles={FRONT_DESK_ROLES}>
              <LazyWrapper>
                <RetentionDashboardPage />
              </LazyWrapper>
            </RoleGate>
          }
        />
        <Route
          path="/crm"
          element={
            <RoleGate allowedRoles={["owner", "manager", "salesperson", "receptionist"]}>
              <LazyWrapper>
                <CrmPage />
              </LazyWrapper>
            </RoleGate>
          }
        />
        <Route
          path="/tasks"
          element={
            <RoleGate allowedRoles={ALL_STAFF_ROLES}>
              <LazyWrapper>
                <TasksPage />
              </LazyWrapper>
            </RoleGate>
          }
        />
        <Route
          path="/goals"
          element={
            <RoleGate allowedRoles={MANAGEMENT_ROLES}>
              <LazyWrapper>
                <GoalsPage />
              </LazyWrapper>
            </RoleGate>
          }
        />
        <Route
          path="/reports"
          element={
            <RoleGate allowedRoles={MANAGEMENT_ROLES}>
              <LazyWrapper>
                <ReportsPage />
              </LazyWrapper>
            </RoleGate>
          }
        />
        <Route
          path="/assessments"
          element={
            <RoleGate allowedRoles={ALL_STAFF_ROLES}>
              <LazyWrapper>
                <AssessmentsPage />
              </LazyWrapper>
            </RoleGate>
          }
        />
        <Route
          path="/assessments/members/:memberId"
          element={
            <RoleGate allowedRoles={ALL_STAFF_ROLES}>
              <LazyWrapper>
                <MemberProfile360Page />
              </LazyWrapper>
            </RoleGate>
          }
        />
        <Route
          path="/assessments/new/:memberId"
          element={
            <RoleGate allowedRoles={ASSESSMENT_WRITE_ROLES}>
              <LazyWrapper>
                <NewAssessmentPage />
              </LazyWrapper>
            </RoleGate>
          }
        />
        <Route
          path="/notifications"
          element={
            <RoleGate allowedRoles={ALL_STAFF_ROLES}>
              <LazyWrapper>
                <NotificationsPage />
              </LazyWrapper>
            </RoleGate>
          }
        />
        <Route
          path="/automations"
          element={
            <RoleGate allowedRoles={MANAGEMENT_ROLES}>
              <LazyWrapper>
                <AutomationsPage />
              </LazyWrapper>
            </RoleGate>
          }
        />
        <Route
          path="/imports"
          element={
            <RoleGate allowedRoles={MANAGEMENT_ROLES}>
              <LazyWrapper>
                <ImportsPage />
              </LazyWrapper>
            </RoleGate>
          }
        />
        <Route
          path="/settings"
          element={
            <LazyWrapper>
              <SettingsPage />
            </LazyWrapper>
          }
        />
        <Route
          path="/settings/users"
          element={
            <RoleGate allowedRoles={MANAGEMENT_ROLES}>
              <LazyWrapper>
                <UsersPage />
              </LazyWrapper>
            </RoleGate>
          }
        />
        <Route
          path="/nps"
          element={
            <RoleGate allowedRoles={["owner", "manager", "receptionist", "salesperson"]}>
              <LazyWrapper>
                <NpsPage />
              </LazyWrapper>
            </RoleGate>
          }
        />
        <Route
          path="/audit"
          element={
            <RoleGate allowedRoles={MANAGEMENT_ROLES}>
              <LazyWrapper>
                <AuditPage />
              </LazyWrapper>
            </RoleGate>
          }
        />
        <Route
          path="/vendas/briefing/:leadId"
          element={
            <RoleGate allowedRoles={SALES_ROLES}>
              <LazyWrapper>
                <SalesBriefingPage />
              </LazyWrapper>
            </RoleGate>
          }
        />
        <Route
          path="/vendas/script/:leadId"
          element={
            <RoleGate allowedRoles={SALES_ROLES}>
              <LazyWrapper>
                <CallScriptPage />
              </LazyWrapper>
            </RoleGate>
          }
        />
      </Route>

      <Route path="*" element={<Navigate to="/dashboard/executive" replace />} />
    </Routes>
  );
}
