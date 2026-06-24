import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import Layout from './components/Layout';
import AuthGate from './components/AuthGate';
import LoginPage from './pages/LoginPage';
import Dashboard from './pages/Dashboard';
import CompetitorList from './pages/CompetitorList';
import CompetitorWorkspacePage from './pages/CompetitorWorkspacePage';
import SignalsFeedPage from './pages/SignalsFeedPage';
import MarketTrends from './pages/MarketTrends';
import WeeklyDigest from './pages/WeeklyDigest';
import SourcesAdmin from './pages/SourcesAdmin';
import CompanyContext from './pages/CompanyContext';
import SearchPage from './pages/SearchPage';
import HowItWorksPage from './pages/HowItWorksPage';
import CrawlRunDetailPage from './pages/CrawlRunDetailPage';
import ScheduleAdmin from './pages/ScheduleAdmin';
import LogsAdmin from './pages/LogsAdmin';
import LlmUsageAdmin from './pages/LlmUsageAdmin';
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
            <Route index element={<Dashboard />} />
            <Route path="competitors" element={<CompetitorList />} />
            <Route path="competitors/:slug" element={<CompetitorWorkspacePage />} />
            <Route path="signals" element={<SignalsFeedPage />} />
            <Route path="trends" element={<MarketTrends />} />
            <Route path="events" element={<EventCalendarPage />} />
            <Route path="digest" element={<WeeklyDigest />} />
            <Route path="search" element={<SearchPage />} />
            <Route path="admin/sources" element={<SourcesAdmin />} />
            <Route path="crawl-runs/:id" element={<CrawlRunDetailPage />} />
            <Route path="context" element={<CompanyContext />} />
            <Route path="how-it-works" element={<HowItWorksPage />} />
            <Route path="admin/schedule" element={<ScheduleAdmin />} />
            <Route path="admin/logs" element={<LogsAdmin />} />
            <Route path="admin/llm-usage" element={<LlmUsageAdmin />} />
          </Route>
        </Routes>
      </BrowserRouter>
    </QueryClientProvider>
  );
}
