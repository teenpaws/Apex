'use client';

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { profileApi } from '@/lib/api/client';
import type { CareerProfile } from '@/types';

export const profileKeys = {
  all: ['profile'] as const,
  detail: () => [...profileKeys.all, 'detail'] as const,
};

export function useProfile() {
  return useQuery({
    queryKey: profileKeys.detail(),
    queryFn: async () => {
      const res = await profileApi.get();
      return res.data as CareerProfile;
    },
  });
}

export function useUpdateProfile() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (data: Partial<CareerProfile>) => {
      const res = await profileApi.update(data as Record<string, unknown>);
      return res.data as CareerProfile;
    },
    onSuccess: (updated) => {
      queryClient.setQueryData(profileKeys.detail(), updated);
    },
  });
}
