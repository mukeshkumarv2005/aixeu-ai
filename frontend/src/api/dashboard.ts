/** Dashboard API hooks — TanStack Query wrappers around the
 * ``/api/v1/dashboard`` and ``/api/v1/dashboard/usage`` endpoints.
 */

import { useQuery } from '@tanstack/react-query'
import { apiClient } from '@/lib/api'
import type { DashboardResponse, UsageResponse } from '@/types/dashboard'

/** Fetch the aggregate dashboard data for the current user. */
export function useDashboard() {
  return useQuery<DashboardResponse>({
    queryKey: ['dashboard'],
    queryFn: () => apiClient.get<DashboardResponse>('/dashboard'),
  })
}

/** Fetch detailed usage analytics with daily breakdown. */
export function useUsage() {
  return useQuery<UsageResponse>({
    queryKey: ['dashboard', 'usage'],
    queryFn: () => apiClient.get<UsageResponse>('/dashboard/usage'),
  })
}
