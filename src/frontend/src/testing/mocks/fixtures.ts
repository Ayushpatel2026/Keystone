import type { DemoUser } from '@/lib/auth'

const timestamps = {
  created_at: '2026-09-01T00:00:00Z',
  updated_at: '2026-09-01T00:00:00Z',
}
const flags = { is_active: true, is_superuser: false, is_verified: true }

export const alice: DemoUser = {
  id: '00000000-0000-4000-8000-000000000001',
  email: 'alice.anderson@mcmaster.ca',
  first_name: 'Alice',
  last_name: 'Anderson',
  role: 'student',
  course_id: '00000000-0000-4000-8000-0000000000c1',
  ...flags,
  ...timestamps,
}

export const david: DemoUser = {
  id: '00000000-0000-4000-8000-000000000002',
  email: 'david.supervisor@example.com',
  first_name: 'David',
  last_name: 'Supervisor',
  role: 'supervisor',
  supervisor_type: 'internal',
  supervisor_verification_status: 'verified',
  ...flags,
  ...timestamps,
}

export const carol: DemoUser = {
  id: '00000000-0000-4000-8000-000000000003',
  email: 'carol.instructor@mcmaster.ca',
  first_name: 'Carol',
  last_name: 'Instructor',
  role: 'instructor',
  course_ids: ['00000000-0000-4000-8000-0000000000c1'],
  ...flags,
  is_superuser: true,
  ...timestamps,
}

export const users: DemoUser[] = [alice, david, carol]

/** A JWT-shaped token for `email` that expires an hour from now. */
export function fakeToken(email: string) {
  const payload = btoa(
    JSON.stringify({ sub: email, exp: Math.floor(Date.now() / 1000) + 3600 }),
  )
  return `header.${payload}.signature`
}
