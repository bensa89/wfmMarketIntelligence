import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { getCurrentUser } from './api/client';
import Layout from './components/Layout';
import AuthGate from './components/AuthGate';
import LoginPage from './pages/LoginPage';
import DashboardPage from './pages/DashboardPage';
import CompetitorListPage from './pages/CompetitorListPage';
import CompetitorWorkspacePage from './pages/CompetitorWorkspacePage';
import SignalsFeedPage from './pages/SignalsFeedPage';
import MarketTrendsPage from './pages/MarketTrendsPage';
import WeeklyDigestPage from './pages/WeeklyDigestPage';
import SourcesAdminPage from './pages/SourcesAdminPage';
import CompanyContextPage from './pages/CompanyContextPage';
import SearchPage from './pages/SearchPage';
import HowItWorksPage from './pages/HowItWorksPage';
import CrawlRunDetailPage from './pages/CrawlRunDetailPage';
import ScheduleAdminPage from './pages/ScheduleAdminPage';
import LogsAdminPage from './pages/LogsAdminPage';
import LlmUsageAdminPage from './pages/LlmUsageAdminPage';
import SettingsAdminPage from './pages/SettingsAdminPage';
import EventCalendarPage from './pages/EventCalendarPage';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 1,
      staleTime: 0,
      refetchOnWindowFocus: true,
    },
  },
});

function AdminOnly({ children }: { children: React.ReactNode }) {
  const user = getCurrentUser();
  if (!user || user.role !== 'admin') return <Navigate to="/" replace />;
  return <>{children}</>;
}

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <Routes>
          <Route path="/login" element={<LoginPage />} />
          <Route
            element={
              <AuthGate>
                <Layout />
              </AuthGate>
            }
          >
            <Route index element={<DashboardPage />} />
            <Route path="competitors" element={<CompetitorListPage />} />
            <Route path="competitors/:slug" element={<CompetitorWorkspacePage />} />
            <Route path="signals" element={<SignalsFeedPage />} />
            <Route path="trends" element={<MarketTrendsPage />} />
            <Route path="events" element={<EventCalendarPage />} />
            <Route path="digest" element={<WeeklyDigestPage />} />
            <Route path="search" element={<SearchPage />} />
            <Route path="admin/sources" element={<SourcesAdminPage />} />
            <Route path="admin/users" element={<AdminOnly>{/* UsersAdminPage added in Task 8 */}<div /></AdminOnly>} />
            <Route path="crawl-runs/:id" element={<CrawlRunDetailPage />} />
            <Route path="context" element={<CompanyContextPage />} />
            <Route path="how-it-works" element={<HowItWorksPage />} />
            <Route path="admin/schedule" element={<ScheduleAdminPage />} />
            <Route path="admin/logs" element={<LogsAdminPage />} />
            <Route path="admin/llm-usage" element={<LlmUsageAdminPage />} />
            <Route path="admin/settings" element={<SettingsAdminPage />} />
          </Route>
        </Routes>
      </BrowserRouter>
    </QueryClientProvider>
  );
}
