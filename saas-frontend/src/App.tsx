import { lazy, Suspense } from "react";
import { Navigate, Route, Routes } from "react-router-dom";

import { LoadingPanel } from "./components/common/LoadingPanel";
import { ProtectedRoute } from "./components/common/ProtectedRoute";
import { AppLayout } from "./layouts/AppLayout";
import { LoginPage } from "./pages/auth/LoginPage";

const ExecutiveDashboardPage = lazy(() => import("./pages/dashboard/ExecutiveDashboardPage").then((m) => ({ default: m.ExecutiveDashboardPage })));
const OperationalDashboardPage = lazy(() => import("./pages/dashboard/OperationalDashboardPage").then((m) => ({ default: m.OperationalDashboardPage })));
const CommercialDashboardPage = lazy(() => import("./pages/dashboard/CommercialDashboardPage").then((m) => ({ default: m.CommercialDashboardPage })));
const FinancialDashboardPage = lazy(() => import("./pages/dashboard/FinancialDashboardPage").then((m) => ({ default: m.FinancialDashboardPage })));
const RetentionDashboardPage = lazy(() => import("./pages/dashboard/RetentionDashboardPage").then((m) => ({ default: m.RetentionDashboardPage })));
const CrmPage = lazy(() => import("./pages/crm/CrmPage").then((m) => ({ default: m.CrmPage })));
const TasksPage = lazy(() => import("./pages/tasks/TasksPage").then((m) => ({ default: m.TasksPage })));
const NotificationsPage = lazy(() => import("./pages/notifications/NotificationsPage").then((m) => ({ default: m.NotificationsPage })));
const AutomationsPage = lazy(() => import("./pages/automations/AutomationsPage").then((m) => ({ default: m.AutomationsPage })));
const GoalsPage = lazy(() => import("./pages/goals/GoalsPage").then((m) => ({ default: m.GoalsPage })));
const AssessmentsPage = lazy(() => import("./pages/assessments/AssessmentsPage").then((m) => ({ default: m.AssessmentsPage })));
const MemberProfile360Page = lazy(() => import("./pages/assessments/MemberProfile360Page").then((m) => ({ default: m.MemberProfile360Page })));
const NewAssessmentPage = lazy(() => import("./pages/assessments/NewAssessmentPage").then((m) => ({ default: m.NewAssessmentPage })));
const ImportsPage = lazy(() => import("./pages/imports/ImportsPage").then((m) => ({ default: m.ImportsPage })));

function LazyWrapper({ children }: { children: React.ReactNode }) {
  return <Suspense fallback={<LoadingPanel text="Carregando modulo..." />}>{children}</Suspense>;
}

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />

      <Route
        element={
          <ProtectedRoute>
            <AppLayout />
          </ProtectedRoute>
        }
      >
        <Route
          path="/dashboard/executive"
          element={
            <LazyWrapper>
              <ExecutiveDashboardPage />
            </LazyWrapper>
          }
        />
        <Route
          path="/dashboard/operational"
          element={
            <LazyWrapper>
              <OperationalDashboardPage />
            </LazyWrapper>
          }
        />
        <Route
          path="/dashboard/commercial"
          element={
            <LazyWrapper>
              <CommercialDashboardPage />
            </LazyWrapper>
          }
        />
        <Route
          path="/dashboard/financial"
          element={
            <LazyWrapper>
              <FinancialDashboardPage />
            </LazyWrapper>
          }
        />
        <Route
          path="/dashboard/retention"
          element={
            <LazyWrapper>
              <RetentionDashboardPage />
            </LazyWrapper>
          }
        />
        <Route
          path="/crm"
          element={
            <LazyWrapper>
              <CrmPage />
            </LazyWrapper>
          }
        />
        <Route
          path="/tasks"
          element={
            <LazyWrapper>
              <TasksPage />
            </LazyWrapper>
          }
        />
        <Route
          path="/goals"
          element={
            <LazyWrapper>
              <GoalsPage />
            </LazyWrapper>
          }
        />
        <Route
          path="/assessments"
          element={
            <LazyWrapper>
              <AssessmentsPage />
            </LazyWrapper>
          }
        />
        <Route
          path="/assessments/members/:memberId"
          element={
            <LazyWrapper>
              <MemberProfile360Page />
            </LazyWrapper>
          }
        />
        <Route
          path="/assessments/new/:memberId"
          element={
            <LazyWrapper>
              <NewAssessmentPage />
            </LazyWrapper>
          }
        />
        <Route
          path="/notifications"
          element={
            <LazyWrapper>
              <NotificationsPage />
            </LazyWrapper>
          }
        />
        <Route
          path="/automations"
          element={
            <LazyWrapper>
              <AutomationsPage />
            </LazyWrapper>
          }
        />
        <Route
          path="/imports"
          element={
            <LazyWrapper>
              <ImportsPage />
            </LazyWrapper>
          }
        />
      </Route>

      <Route path="*" element={<Navigate to="/dashboard/executive" replace />} />
    </Routes>
  );
}
