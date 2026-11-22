import { http, HttpResponse } from 'msw'
import { setupServer } from 'msw/node'
import { DEMO_PASSWORD } from '@/lib/auth'
import { fakeToken, users } from '@/testing/mocks/fixtures'

/**
 * A fake backend for tests. These handlers answer by default; a test can
 * override one with `server.use(http.get('/api/...', () => ...))`, and the
 * override is dropped after that test.
 */
export const server = setupServer(
  http.get('/api/users', () => HttpResponse.json(users)),
  http.get('/api/projects', () => HttpResponse.json([])),
  http.get('/api/courses', () => HttpResponse.json([])),

  http.post('/auth/login', async ({ request }) => {
    const form = new URLSearchParams(await request.text())
    const known = users.some((user) => user.email === form.get('username'))
    if (!known || form.get('password') !== DEMO_PASSWORD) {
      return HttpResponse.json(
        { detail: 'LOGIN_BAD_CREDENTIALS' },
        { status: 400 },
      )
    }
    return HttpResponse.json({
      access_token: fakeToken(form.get('username') ?? ''),
      token_type: 'bearer',
    })
  }),
)
