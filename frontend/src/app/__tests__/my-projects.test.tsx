import { screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { http, HttpResponse } from 'msw'
import { beforeEach, describe, expect, it } from 'vitest'
import { actAs } from '@/lib/auth'
import { david } from '@/testing/mocks/fixtures'
import { project } from '@/testing/mocks/projects'
import { server } from '@/testing/mocks/server'
import {
  agreed,
  teamAgreed,
  teamUnderReview,
  teams,
} from '@/testing/mocks/teams'
import { renderApp } from '@/testing/test-utils'

// Team Alpha has applied and waits for David's decision; Team Delta agreed.
const applied = {
  id: '00000000-0000-4000-8000-0000000000e1',
  team_id: teamUnderReview.id,
  project_id: project.id,
  status: 'applied' as const,
  created_at: '2026-09-10T00:00:00Z',
  updated_at: '2026-09-10T00:00:00Z',
}
const applications = [applied, agreed]

function projectCard() {
  const heading = screen.getByRole('heading', { name: project.title })
  return within(heading.closest('section') as HTMLElement)
}

describe('my projects (supervisor decisions)', () => {
  beforeEach(async () => {
    await actAs(david)
    server.use(
      http.get('/api/projects', ({ request }) => {
        // The page asks only for this supervisor's projects.
        const supervisor = new URL(request.url).searchParams.get(
          'supervisor_id',
        )
        return HttpResponse.json(supervisor === david.id ? [project] : [])
      }),
      http.get('/api/applications', () => HttpResponse.json(applications)),
      http.get('/api/teams', () => HttpResponse.json(teams)),
    )
  })

  it('lists applications per project, with actions only on pending ones', async () => {
    renderApp('/my-projects')
    await screen.findByRole('heading', { name: project.title })

    const card = projectCard()
    expect(card.getByText(/1 waiting for your decision/)).toBeInTheDocument()
    expect(card.getByText(teamUnderReview.name)).toBeInTheDocument()
    expect(card.getByText('Applied')).toBeInTheDocument()
    expect(
      card.getByRole('button', { name: `Accept ${teamUnderReview.name}` }),
    ).toBeInTheDocument()
    expect(
      card.getByRole('button', { name: `Decline ${teamUnderReview.name}` }),
    ).toBeInTheDocument()

    expect(card.getByText(teamAgreed.name)).toBeInTheDocument()
    expect(card.getByText('Agreed')).toBeInTheDocument()
    expect(
      card.queryByRole('button', { name: `Accept ${teamAgreed.name}` }),
    ).not.toBeInTheDocument()
  })

  it('does nothing when the confirmation is cancelled', async () => {
    let calls = 0
    server.use(
      http.post(`/api/applications/${applied.id}/accept`, () => {
        calls += 1
        return HttpResponse.json({ ...applied, status: 'supervisor_accepts' })
      }),
    )
    const user = userEvent.setup()
    renderApp('/my-projects')
    await user.click(
      await screen.findByRole('button', {
        name: `Accept ${teamUnderReview.name}`,
      }),
    )
    const dialog = await screen.findByRole('dialog', {
      name: 'Accept this team?',
    })
    await user.click(within(dialog).getByRole('button', { name: 'Cancel' }))

    await waitFor(() => {
      expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
    })
    expect(calls).toBe(0)
  })

  it.each([
    ['accept', 'Accept', 'supervisor_accepts', 'accepted'],
    ['decline', 'Decline', 'declined_or_withdrawn', 'declined'],
  ] as const)(
    'sends the %s after confirmation and refreshes the list',
    async (decision, label, newStatus, pastTense) => {
      let called = false
      server.use(
        http.post(`/api/applications/${applied.id}/${decision}`, () => {
          called = true
          return HttpResponse.json({ ...applied, status: newStatus })
        }),
      )
      const user = userEvent.setup()
      renderApp('/my-projects')
      await user.click(
        await screen.findByRole('button', {
          name: `${label} ${teamUnderReview.name}`,
        }),
      )
      const dialog = await screen.findByRole('dialog')

      // The list reloads after the decision; serve the updated status.
      server.use(
        http.get('/api/applications', () =>
          HttpResponse.json([{ ...applied, status: newStatus }, agreed]),
        ),
      )
      await user.click(within(dialog).getByRole('button', { name: label }))

      expect(
        await screen.findByText(
          new RegExp(`${teamUnderReview.name} was ${pastTense}`),
        ),
      ).toBeInTheDocument()
      expect(called).toBe(true)
      expect(
        await screen.findByText(/0 waiting for your decision/),
      ).toBeInTheDocument()
      expect(
        screen.queryByRole('button', {
          name: `${label} ${teamUnderReview.name}`,
        }),
      ).not.toBeInTheDocument()
    },
  )

  it("shows the backend's message when it refuses the action", async () => {
    const detail = 'The project has no free slots left'
    server.use(
      http.post(`/api/applications/${applied.id}/accept`, () =>
        HttpResponse.json({ detail }, { status: 409 }),
      ),
    )
    const user = userEvent.setup()
    renderApp('/my-projects')
    await user.click(
      await screen.findByRole('button', {
        name: `Accept ${teamUnderReview.name}`,
      }),
    )
    const dialog = await screen.findByRole('dialog')
    await user.click(within(dialog).getByRole('button', { name: 'Accept' }))

    expect(await within(dialog).findByRole('alert')).toHaveTextContent(detail)
    expect(screen.getByRole('dialog')).toBeInTheDocument()
  })

  it('says so when the supervisor has no projects', async () => {
    server.use(http.get('/api/projects', () => HttpResponse.json([])))
    renderApp('/my-projects')
    expect(
      await screen.findByText("You don't have any projects yet."),
    ).toBeInTheDocument()
  })

  it('shows an error with retry when loading fails', async () => {
    server.use(
      http.get('/api/applications', () =>
        HttpResponse.json({}, { status: 500 }),
      ),
    )
    renderApp('/my-projects')
    expect(await screen.findByRole('alert')).toHaveTextContent(
      'Could not load your projects and applications.',
    )
    expect(screen.getByRole('button', { name: 'Retry' })).toBeInTheDocument()
  })
})
