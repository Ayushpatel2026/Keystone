import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useSyncExternalStore } from 'react'
import { api } from '../api/client'
import { actAs, getActingAs, subscribe, type DemoUser } from './session'

/**
 * The user the app is acting as, or null if nobody is picked. Re-renders when
 * someone switches user.
 *
 *   const user = useActingAs()
 *   if (user?.role !== 'student') return <p>Pick a student to apply.</p>
 */
export function useActingAs(): DemoUser | null {
  return useSyncExternalStore(subscribe, getActingAs)
}

/**
 * Switch who the app acts as. Clears all cached server data, since what the
 * API returns depends on who is asking.
 */
export function useSwitchUser() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: actAs,
    onSuccess: () => queryClient.resetQueries(),
  })
}

/** Every user, for the switcher. */
export function useUsers() {
  return useQuery({
    queryKey: ['users'],
    queryFn: async () => {
      const { data, error } = await api.GET('/api/users')
      if (error) throw new Error('Could not load users.', { cause: error })
      return data
    },
  })
}
