import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import type { Middleware } from 'openapi-fetch'
import { useSyncExternalStore } from 'react'
import { api } from '@/lib/api-client'
import type { paths } from '@/types/api'

/*
 * Demo sign-in: who the app is acting as, and their token.
 *
 * The PoC has no real sign-in (Development Plan, section 9). The user picks
 * who to act as in the switcher, and the app signs in as them with the seed
 * password. This module adds that user's token to every request made with
 * `api` from `@/lib/api-client`.
 */

/** A user as `GET /api/users` returns them (student, TA, instructor or supervisor). */
export type DemoUser =
  paths['/api/users']['get']['responses'][200]['content']['application/json'][number]

/**
 * The password every seeded account shares (`SEED_PASSWORD` in
 * src/backend/app/core/seed.py). The PoC has no real sign-in: the user picks
 * who to act as, and the app signs in as them behind the scenes. Accounts
 * made through /auth/register have their own passwords, so only seeded users
 * can be picked.
 */
export const DEMO_PASSWORD = 'dev-password-123'

const STORAGE_KEY = 'keystone.actingAs'

// Sign in again this long before the token expires, so requests don't race it.
const REFRESH_MARGIN_MS = 60_000

interface Session {
  user: DemoUser
  token: string | null
  /** Milliseconds since the epoch. */
  expiresAt: number
}

let session: Session | null = readStoredSession()
let pendingLogin: Promise<string> | null = null
const listeners = new Set<() => void>()

/** The user the app is acting as, or null. */
export function getActingAs(): DemoUser | null {
  return session?.user ?? null
}

/** For useSyncExternalStore: call `listener` whenever the user changes. */
export function subscribe(listener: () => void) {
  listeners.add(listener)
  return () => {
    listeners.delete(listener)
  }
}

/**
 * Act as `user` (or nobody). Signs in first, so a failure leaves the current
 * user in place and the caller can show the error.
 */
export async function actAs(user: DemoUser | null): Promise<void> {
  pendingLogin = null
  if (user === null) {
    setSession(null)
    return
  }
  const { token, expiresAt } = await signIn(user.email)
  setSession({ user, token, expiresAt })
}

/** Swap in fresh details for the current user (for example after a reseed). */
export function updateActingAs(user: DemoUser) {
  if (!session) return
  // A different id means the database was reseeded: the old token names a
  // user that no longer exists, so sign in again on the next request.
  const token = session.user.id === user.id ? session.token : null
  setSession({ ...session, user, token })
}

/** Adds `Authorization: Bearer …` to every API request while acting as someone. */
const authMiddleware: Middleware = {
  async onRequest({ request, schemaPath }) {
    // Signing in needs no token, and asking for one here would sign in again.
    if (schemaPath === '/auth/login') return request
    const token = await currentToken()
    if (token) request.headers.set('Authorization', `Bearer ${token}`)
    return request
  },
}
api.use(authMiddleware)
// When Vite hot-reloads this file, take the old middleware off first.
import.meta.hot?.dispose(() => {
  api.eject(authMiddleware)
})

/** Forget the user and token. Tests call this between cases. */
export function resetSession() {
  pendingLogin = null
  setSession(null)
}

async function currentToken(): Promise<string | null> {
  if (!session) return null
  if (session.token && session.expiresAt - REFRESH_MARGIN_MS > Date.now()) {
    return session.token
  }
  // Expired, or restored without a token: sign in again, once for all the
  // requests waiting on it.
  if (!pendingLogin) {
    const forUser = session.user
    pendingLogin = signIn(forUser.email).then(({ token, expiresAt }) => {
      // Skip if someone switched user while this was in flight.
      if (session?.user.id === forUser.id) {
        setSession({ user: forUser, token, expiresAt })
        pendingLogin = null
      }
      return token
    })
    pendingLogin.catch(() => {
      pendingLogin = null
    })
  }
  return pendingLogin
}

async function signIn(email: string) {
  const { data, error } = await api.POST('/auth/login', {
    body: { username: email, password: DEMO_PASSWORD, scope: '' },
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
  })
  if (!data) {
    throw new SignInError(email, error)
  }
  return {
    token: data.access_token,
    expiresAt: tokenExpiry(data.access_token),
  }
}

export class SignInError extends Error {
  readonly email: string
  readonly detail: unknown

  constructor(email: string, detail: unknown) {
    super(`Couldn't sign in as ${email}.`)
    this.name = 'SignInError'
    this.email = email
    this.detail = detail
  }
}

/** The `exp` claim of a JWT, in milliseconds. */
function tokenExpiry(token: string): number {
  try {
    const payload = token.split('.')[1].replace(/-/g, '+').replace(/_/g, '/')
    const { exp } = JSON.parse(atob(payload)) as { exp?: unknown }
    if (typeof exp === 'number') return exp * 1000
  } catch {
    // Not a JWT we can read; fall through.
  }
  // The backend's default lifetime is an hour; assume less to be safe.
  return Date.now() + 30 * 60_000
}

function setSession(next: Session | null) {
  session = next
  try {
    if (next) localStorage.setItem(STORAGE_KEY, JSON.stringify(next))
    else localStorage.removeItem(STORAGE_KEY)
  } catch {
    // Storage blocked (private mode etc.): the choice just won't survive a reload.
  }
  listeners.forEach((listener) => {
    listener()
  })
}

function readStoredSession(): Session | null {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (!raw) return null
    const stored = JSON.parse(raw) as Partial<Session>
    if (!stored.user?.id || !stored.user.email) return null
    return {
      user: stored.user,
      token: stored.token ?? null,
      expiresAt: stored.expiresAt ?? 0,
    }
  } catch {
    return null
  }
}

// React hooks

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
