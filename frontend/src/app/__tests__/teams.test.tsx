import { screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { http, HttpResponse } from 'msw'
import { beforeEach, describe, expect, it } from 'vitest'
import { actAs } from '@/lib/auth'
import { carol } from '@/testing/mocks/fixtures'
import { course, project } from '@/testing/mocks/projects'
import { server } from '@/testing/mocks/server'
import { applications, teams, underReview } from '@/testing/mocks/teams'
import { renderApp } from '@/testing/test-utils'

function section(name: RegExp) {
  const heading = screen.getByRole('heading', { name })
  return within(heading.closest('section') as HTMLElement)
}

describe('teams review page', () => {
  beforeEach(async () => {
    await actAs(carol)
    server.use(
      http.get('/api/applications', () => HttpResponse.json(applications)),
      http.get('/api/teams', () => HttpResponse.json(teams)),
      http.get('/api/projects', () => HttpResponse.json([project])),
      http.get('/api/courses', () => HttpResponse.json([course])),
    )
  })

  it('lists submissions under review with actions, and decided ones without', async () => {
    renderApp('/teams')
    await screen.findByRole('heading', { name: /Awaiting review \(1\)/ })

    const toReview = section(/Awaiting review/)
    expect(await toReview.findByText('Team Alpha')).toBeInTheDocument()
    expect(toReview.getByText('Under review')).toBeInTheDocument()
    expect(
      toReview.getByRole('button', { name: 'Approve Team Alpha' }),
    ).toBeInTheDocument()
    expect(
      toReview.getByRole('button', { name: 'Reject Team Alpha' }),
    ).toBeInTheDocument()

    const decided = section(/Reviewed \(2\)/)
    expect(decided.getByText('Team Beta')).toBeInTheDocument()
    expect(decided.getByText('Approved')).toBeInTheDocument()
    expect(decided.getByText('Team Gamma')).toBeInTheDocument()
    expect(decided.getByText('Rejected')).toBeInTheDocument()
    expect(decided.queryByRole('button')).not.toBeInTheDocument()

    // Not yet submitted, so not for staff review.
    expect(screen.queryByText('Team Delta')).not.toBeInTheDocument()
  })

  it('does nothing when the confirmation is cancelled', async () => {
    let calls = 0
    server.use(
      http.post(`/api/applications/${underReview.id}/approve`, () => {
        calls += 1
        return HttpResponse.json({ ...underReview, status: 'approved' })
      }),
    )
    const user = userEvent.setup()
    renderApp('/teams')
    await user.click(
      await screen.findByRole('button', { name: 'Approve Team Alpha' }),
    )

    const dialog = await screen.findByRole('dialog', {
      name: 'Approve this team project?',
    })
    await user.click(within(dialog).getByRole('button', { name: 'Cancel' }))

    await waitFor(() => {
      expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
    })
    expect(calls).toBe(0)
  })

  it.each([
    ['approve', 'Approve', 'approved', 'approved'],
    ['reject', 'Reject', 'team_project_rejected', 'rejected'],
  ] as const)(
    'sends the %s after confirmation and refreshes the list',
    async (decision, label, newStatus, pastTense) => {
      const updated = applications.map((item) =>
        item.id === underReview.id ? { ...item, status: newStatus } : item,
      )
      let called = false
      server.use(
        http.post(`/api/applications/${underReview.id}/${decision}`, () => {
          called = true
          return HttpResponse.json({ ...underReview, status: newStatus })
        }),
      )
      const user = userEvent.setup()
      renderApp('/teams')
      await user.click(
        await screen.findByRole('button', { name: `${label} Team Alpha` }),
      )
      const dialog = await screen.findByRole('dialog')

      // The list reloads after the decision; serve the updated status.
      server.use(
        http.get('/api/applications', () => HttpResponse.json(updated)),
      )
      await user.click(within(dialog).getByRole('button', { name: label }))

      expect(
        await screen.findByText(new RegExp(`Team Alpha was ${pastTense}`)),
      ).toBeInTheDocument()
      expect(called).toBe(true)
      expect(
        await screen.findByRole('heading', { name: /Awaiting review \(0\)/ }),
      ).toBeInTheDocument()
      const decided = section(/Reviewed \(3\)/)
      expect(decided.getByText('Team Alpha')).toBeInTheDocument()
    },
  )

  it("shows the backend's message when it refuses the action", async () => {
    const detail =
      'instructor_approve is not allowed from team_project_rejected'
    server.use(
      http.post(`/api/applications/${underReview.id}/approve`, () =>
        HttpResponse.json({ detail }, { status: 409 }),
      ),
    )
    const user = userEvent.setup()
    renderApp('/teams')
    await user.click(
      await screen.findByRole('button', { name: 'Approve Team Alpha' }),
    )
    const dialog = await screen.findByRole('dialog')
    await user.click(within(dialog).getByRole('button', { name: 'Approve' }))

    // The dialog stays open with the reason, so the reviewer sees what happened.
    expect(await within(dialog).findByRole('alert')).toHaveTextContent(detail)
    expect(screen.getByRole('dialog')).toBeInTheDocument()
  })

  it('shows an error with retry when submissions fail to load', async () => {
    server.use(
      http.get('/api/applications', () =>
        HttpResponse.json({}, { status: 500 }),
      ),
    )
    renderApp('/teams')
    expect(await screen.findByRole('alert')).toHaveTextContent(
      'Could not load team submissions.',
    )
    expect(screen.getByRole('button', { name: 'Retry' })).toBeInTheDocument()
  })
})
