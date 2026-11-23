import type { components } from '@/types/api'
import { alice } from '@/testing/mocks/fixtures'
import { course, project } from '@/testing/mocks/projects'

type Application = components['schemas']['ApplicationRead']
type Team = components['schemas']['TeamRead']

const timestamps = {
  created_at: '2026-09-10T00:00:00Z',
  updated_at: '2026-09-12T00:00:00Z',
}

function team(id: string, name: string): Team {
  return {
    id,
    name,
    course_id: course.id,
    members: [
      {
        user: {
          id: alice.id,
          first_name: alice.first_name,
          last_name: alice.last_name,
          email: alice.email,
        },
        student_number: '400000001',
        joined_at: '2026-09-05T00:00:00Z',
      },
    ],
    ...timestamps,
  }
}

export const teamApplying = team(
  '00000000-0000-4000-8000-0000000000b0',
  'Team Amazing Engineers',
)

export const teamUnderReview = team(
  '00000000-0000-4000-8000-0000000000b1',
  'Team Alpha',
)
export const teamApproved = team(
  '00000000-0000-4000-8000-0000000000b2',
  'Team Beta',
)
export const teamRejected = team(
  '00000000-0000-4000-8000-0000000000b3',
  'Team Gamma',
)
export const teamAgreed = team(
  '00000000-0000-4000-8000-0000000000b4',
  'Team Delta',
)

function application(
  id: string,
  teamId: string,
  status: Application['status'],
): Application {
  return { id, team_id: teamId, project_id: project.id, status, ...timestamps }
}

export const underReview = application(
  '00000000-0000-4000-8000-0000000000d1',
  teamUnderReview.id,
  'team_project_under_review',
)
export const approved = application(
  '00000000-0000-4000-8000-0000000000d2',
  teamApproved.id,
  'approved',
)
export const rejected = application(
  '00000000-0000-4000-8000-0000000000d3',
  teamRejected.id,
  'team_project_rejected',
)
/** Not yet submitted: shouldn't appear on the staff review page. */
export const agreed = application(
  '00000000-0000-4000-8000-0000000000d4',
  teamAgreed.id,
  'agreed',
)

export const teams = [teamUnderReview, teamApproved, teamRejected, teamAgreed]
export const applications = [underReview, approved, rejected, agreed]
