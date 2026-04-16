import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import Layout from './components/Layout';
import AuthGate from './components/AuthGate';
import LoginPage from './pages/LoginPage';
import Dashboard from './pages/Dashboard';
import CompetitorList from './pages/CompetitorList';
import CompetitorDetail from './pages/CompetitorDetail';
import MarketTrends from './pages/MarketTrends';
import WeeklyDigest from './pages/WeeklyDigest';
import SourcesAdmin from './pages/SourcesAdmin';
import CompanyContext from './pages/CompanyContext';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 1,
      staleTime: 30_000,
      refetchOnWindowFocus: false,
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
            <Route path="competitors/:slug" element={<CompetitorDetail />} />
            <Route path="trends" element={<MarketTrends />} />
            <Route path="digest" element={<WeeklyDigest />} />
            <Route path="admin/sources" element={<SourcesAdmin />} />
            <Route path="context" element={<CompanyContext />} />
          </Route>
        </Routes>
      </BrowserRouter>
    </QueryClientProvider>
  );
}
