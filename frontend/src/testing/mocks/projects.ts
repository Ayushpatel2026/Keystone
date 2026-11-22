import type { components } from '@/types/api'
import { david } from '@/testing/mocks/fixtures'

export const course: components['schemas']['CourseRead'] = {
  id: '00000000-0000-4000-8000-0000000000c1',
  code: 'SFWRENG 4G06',
  name: 'Software Engineering Capstone',
  program: 'se',
  created_at: '2026-09-01T00:00:00Z',
  updated_at: '2026-09-01T00:00:00Z',
}

export const project: components['schemas']['ProjectRead'] = {
  id: '00000000-0000-4000-8000-0000000000a1',
  title: 'Automated Assembly Line',
  background: 'Automate assembly tasks using sensors.',
  supervisor_id: david.id,
  course_id: course.id,
  supervisor_capacity: 2,
  slots_reserved: 1,
  slots_available: 1,
  status: 'open',
  created_at: '2026-09-01T00:00:00Z',
  updated_at: '2026-09-02T12:00:00Z',
}
