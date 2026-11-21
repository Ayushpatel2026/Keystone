import type { DemoUser } from '@/lib/auth'

export type Role = DemoUser['role']

/** Instructors and TAs, who run the course (SRS: "course staff"). */
export const courseStaff: Role[] = ['instructor', 'ta']

/** How to name a role in a sentence: "a student", "an instructor". */
export const roleWithArticle: Record<Role, string> = {
  student: 'a student',
  supervisor: 'a supervisor',
  instructor: 'an instructor',
  ta: 'a TA',
}

/** Who a page is for, as a phrase: "students", "course staff". */
export function audience(roles: Role[]): string {
  if (courseStaff.every((role) => roles.includes(role)) && roles.length === 2) {
    return 'course staff (instructors and TAs)'
  }
  const plural: Record<Role, string> = {
    student: 'students',
    supervisor: 'supervisors',
    instructor: 'instructors',
    ta: 'TAs',
  }
  return roles.map((role) => plural[role]).join(' and ')
}
