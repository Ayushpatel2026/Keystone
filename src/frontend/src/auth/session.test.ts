import { http, HttpResponse } from 'msw'
import { describe, expect, it } from 'vitest'
import { api } from '../api/client'
import { alice, david } from '../test/fixtures'
import { server } from '../test/server'
import { actAs, getActingAs, updateActingAs } from './session'

/** Record the Authorization header of the next /api/health request. */
function captureAuthorization() {
  const seen: (string | null)[] = []
  server.use(
    http.get('/api/health', ({ request }) => {
      seen.push(request.headers.get('Authorization'))
      return HttpResponse.json({ status: 'ok' })
    }),
  )
  return seen
}

/** Count logins, answering each with a token that expires in `seconds`. */
function countLogins(seconds: number) {
  let count = 0
  server.use(
    http.post('/auth/login', () => {
      count += 1
      const exp = Math.floor(Date.now() / 1000) + seconds
      const payload = btoa(JSON.stringify({ exp, n: count }))
      return HttpResponse.json({
        access_token: `header.${payload}.signature`,
        token_type: 'bearer',
      })
    }),
  )
  return () => count
}

describe('session', () => {
  it('sends no token while acting as nobody', async () => {
    const seen = captureAuthorization()
    await api.GET('/api/health')
    expect(seen).toEqual([null])
  })

  it('reuses a fresh token', async () => {
    const logins = countLogins(3600)
    await actAs(alice)
    const seen = captureAuthorization()
    await api.GET('/api/health')
    await api.GET('/api/health')
    expect(logins()).toBe(1)
    expect(seen[0]).toBe(seen[1])
  })

  it('signs in again, once, when the token is about to expire', async () => {
    const logins = countLogins(30) // inside the one-minute margin
    await actAs(alice)
    const seen = captureAuthorization()
    await Promise.all([api.GET('/api/health'), api.GET('/api/health')])
    // One login for the switch, one shared by both requests.
    expect(logins()).toBe(2)
    expect(seen).toHaveLength(2)
    expect(seen[0]).toBe(seen[1])
  })

  it('drops the token when a reseed changes the user id', async () => {
    await actAs(alice)
    const logins = countLogins(3600)
    updateActingAs({ ...alice, id: '00000000-0000-4000-8000-0000000000aa' })
    await api.GET('/api/health').catch(() => undefined)
    expect(logins()).toBe(1)
    expect(getActingAs()?.id).toBe('00000000-0000-4000-8000-0000000000aa')
  })

  it('keeps the previous user when sign-in fails', async () => {
    await actAs(alice)
    server.use(
      http.post('/auth/login', () =>
        HttpResponse.json({ detail: 'LOGIN_BAD_CREDENTIALS' }, { status: 400 }),
      ),
    )
    await expect(actAs(david)).rejects.toThrow(
      `Couldn't sign in as ${david.email}`,
    )
    expect(getActingAs()?.id).toBe(alice.id)
  })
})
