import { hasCredentials } from '../api/client';
import { Navigate } from 'react-router-dom';

export default function AuthGate({ children }: { children: React.ReactNode }) {
  if (!hasCredentials()) {
    return <Navigate to="/login" replace />;
  }
  return <>{children}</>;
}
