'use client';

import { useQuery } from '@tanstack/react-query';
import { analyticsApi } from '@/lib/api/client';
import type { DashboardStats } from '@/types';

export const dashboardKeys = {
  all: ['dashboard'] as const,
  stats: () => [...dashboardKeys.all, 'stats'] as const,
};

export function useDashboardStats() {
  return useQuery({
    queryKey: dashboardKeys.stats(),
    queryFn: async () => {
      const res = await analyticsApi.dashboard();
      return res.data as DashboardStats;
    },
    refetchInterval: 5 * 60 * 1000,
  });
}
