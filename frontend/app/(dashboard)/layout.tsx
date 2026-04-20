import { DashboardLayout } from '@/components/layout/DashboardLayout';
import ErrorBoundary from '@/components/ErrorBoundary';

export default function Layout({ children }: { children: React.ReactNode }) {
  return <DashboardLayout><ErrorBoundary>{children}</ErrorBoundary></DashboardLayout>;
}
