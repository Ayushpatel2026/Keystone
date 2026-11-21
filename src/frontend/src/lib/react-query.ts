import { QueryClient } from '@tanstack/react-query'

/**
 * Shared cache for server data. Components read with `useQuery` and change
 * data with `useMutation`; after a change, invalidate the affected keys so
 * every screen showing that data refetches.
 */
export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      // Retrying a 4xx (for example a rejected action) just repeats the error.
      retry: 1,
      refetchOnWindowFocus: true,
    },
  },
})
