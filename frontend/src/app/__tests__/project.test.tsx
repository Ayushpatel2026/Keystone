import { screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { delay, http, HttpResponse } from 'msw'
import { describe, expect, it } from 'vitest'
import { actAs } from '@/lib/auth'
import { alice, david } from '@/testing/mocks/fixtures'
import { course, project } from '@/testing/mocks/projects'
import { server } from '@/testing/mocks/server'
import { teamApplying } from '@/testing/mocks/teams'
import { renderApp } from '@/testing/test-utils'

describe('project details', () => {
  it.each([
    { status: 'open', label: 'Open', reserved: 1, available: 1 },
    { status: 'full', label: 'Full', reserved: 2, available: 0 },
    { status: 'closed', label: 'Closed', reserved: 1, available: 1 },
  ] as const)(
    'displays $label project details and slot counts',
    async ({ status, label, reserved, available }) => {
      // Closed projects may still have free slots, while Full projects have none.
      server.use(
        http.get(`/api/projects/${project.id}`, () =>
          HttpResponse.json({
            ...project,
            status,
            slots_reserved: reserved,
            slots_available: available,
          }),
        ),
      )
      renderApp(`/projects/${project.id}`)
      await screen.findByRole('heading', { name: project.title })
      expect(screen.getByText(label)).toBeInTheDocument()
      expect(screen.getByText('Capacity: 2 teams')).toBeInTheDocument()
      expect(
        screen.getByText(`Reserved slots: ${reserved}`),
      ).toBeInTheDocument()
      expect(
        screen.getByText(`Available slots: ${available}`),
      ).toBeInTheDocument()
    },
  )

  it('loads the requested project and shows its details and readable names', async () => {
    // The selected URL loads the correct project, background, course, and supervisor.
    server.use(
      http.get(`/api/projects/${project.id}`, () => HttpResponse.json(project)),
      http.get('/api/courses', () => HttpResponse.json([course])),
    )
    renderApp(`/projects/${project.id}`)
    expect(
      await screen.findByRole('heading', { name: project.title }),
    ).toBeInTheDocument()
    expect(screen.getByText(project.background)).toBeInTheDocument()
    expect(
      await screen.findByText(`Course: ${course.code} - ${course.name}`),
    ).toBeInTheDocument()
    expect(
      await screen.findByText('Supervisor: David Supervisor'),
    ).toBeInTheDocument()
    expect(screen.getByText(/Last updated:/)).toBeInTheDocument()
  })

  it('returns to the catalog using the back link', async () => {
    // The details page provides working navigation back to the catalog.
    server.use(
      http.get(`/api/projects/${project.id}`, () => HttpResponse.json(project)),
    )
    const user = userEvent.setup()
    const { router } = renderApp(`/projects/${project.id}`)
    await screen.findByRole('heading', { name: project.title })
    await user.click(screen.getByRole('link', { name: 'Back to projects' }))
    expect(
      await screen.findByRole('heading', { name: 'Projects' }),
    ).toBeInTheDocument()
    expect(router.state.location.pathname).toBe('/projects')
  })

  it('shows loading while the details request is pending', async () => {
    // The loading indicator disappears when the project response arrives.
    server.use(
      http.get(`/api/projects/${project.id}`, async () => {
        await delay(150)
        return HttpResponse.json(project)
      }),
    )
    renderApp(`/projects/${project.id}`)
    expect(
      screen.getByRole('progressbar', { name: 'Loading project' }),
    ).toBeInTheDocument()
    await screen.findByRole('heading', { name: project.title })
    expect(
      screen.queryByRole('progressbar', { name: 'Loading project' }),
    ).not.toBeInTheDocument()
  })

  it.each([
    [404, 'Project not found.'],
    [500, 'Could not load project.'],
  ])('shows the appropriate error for HTTP %s', async (status, message) => {
    // Missing projects and server failures show an error instead of project details.
    server.use(
      http.get(`/api/projects/${project.id}`, () =>
        HttpResponse.json({}, { status }),
      ),
    )
    renderApp(`/projects/${project.id}`)
    expect(await screen.findByRole('alert')).toHaveTextContent(message)
    expect(
      screen.queryByRole('heading', { name: project.title }),
    ).not.toBeInTheDocument()
  })
})

describe('applying to a project', () => {
  it('submits the current student, team, and project and refreshes applications', async () => {
    // Apply sends the correct IDs, blocks repeat clicks, and refreshes cached applications.
    let submitted: unknown
    let studentId: string | null = null
    let applicationReads = 0
    const createdApplication = {
      id: '00000000-0000-4000-8000-0000000000d1',
      team_id: teamApplying.id,
      project_id: project.id,
      status: 'applied',
      created_at: project.created_at,
      updated_at: project.updated_at,
    }
    server.use(
      http.get(`/api/projects/${project.id}`, () => HttpResponse.json(project)),
      http.get('/api/projects', () => HttpResponse.json([project])),
      http.get('/api/teams', () => HttpResponse.json([teamApplying])),
      http.get('/api/applications', () => {
        applicationReads += 1
        return HttpResponse.json(submitted ? [createdApplication] : [])
      }),
      http.post('/api/applications', async ({ request }) => {
        submitted = await request.json()
        studentId = new URL(request.url).searchParams.get('student_id')
        await delay(100)
        return HttpResponse.json(createdApplication, { status: 201 })
      }),
    )
    await actAs(alice)
    const user = userEvent.setup()
    const { router } = renderApp('/team')
    await screen.findByText("Your team hasn't applied to any projects yet.")
    // Navigate within the same app so the team's application query stays cached.
    await waitFor(() => expect(applicationReads).toBeGreaterThan(0))
    const previousReads = applicationReads
    await router.navigate(`/projects/${project.id}`)
    const button = await screen.findByRole('button', { name: 'Apply' })
    await user.click(button)
    expect(
      await screen.findByRole('button', { name: 'Applying…' }),
    ).toBeDisabled()
    await screen.findByText('Your team has applied to this project.')
    expect(submitted).toEqual({
      team_id: teamApplying.id,
      project_id: project.id,
    })
    expect(studentId).toBe(alice.id)
    expect(screen.getByRole('button', { name: 'Apply' })).toBeDisabled()
    // Inactive queries refetch when the user returns to My Team.
    await router.navigate('/team')
    await screen.findByText('Applied')
    expect(
      screen.getByRole('heading', { name: project.title }),
    ).toBeInTheDocument()
    expect(applicationReads).toBeGreaterThan(previousReads)
  })

  it.each([
    'The team has already applied to this project',
    'The team has already agreed to a project',
    'Project is not open for applications (status: full)',
  ])('shows the backend rejection: %s', async (message) => {
    // Duplicate, agreement, and stale-project conflicts retain the backend explanation.
    server.use(
      http.get(`/api/projects/${project.id}`, () => HttpResponse.json(project)),
      http.get('/api/teams', () => HttpResponse.json([teamApplying])),
      http.post('/api/applications', () =>
        HttpResponse.json({ detail: message }, { status: 409 }),
      ),
    )
    await actAs(alice)
    const user = userEvent.setup()
    renderApp(`/projects/${project.id}`)
    await user.click(await screen.findByRole('button', { name: 'Apply' }))
    expect(await screen.findByText(message)).toBeInTheDocument()
    expect(
      screen.queryByText('Your team has applied to this project.'),
    ).not.toBeInTheDocument()
  })

  it('requires a team before applying', async () => {
    // Students without a team see guidance instead of an Apply button.
    server.use(
      http.get(`/api/projects/${project.id}`, () => HttpResponse.json(project)),
      http.get('/api/teams', () => HttpResponse.json([])),
    )
    await actAs(alice)
    renderApp(`/projects/${project.id}`)
    await screen.findByText('You must belong to a team before applying.')
    expect(
      screen.queryByRole('button', { name: 'Apply' }),
    ).not.toBeInTheDocument()
  })

  it.each(['full', 'closed'] as const)(
    'does not offer Apply for a %s project',
    async (status) => {
      // Full and Closed projects cannot receive applications through the UI.
      server.use(
        http.get(`/api/projects/${project.id}`, () =>
          HttpResponse.json({ ...project, status }),
        ),
      )
      await actAs(alice)
      renderApp(`/projects/${project.id}`)
      await screen.findByText('This project is not open for applications.')
      expect(
        screen.queryByRole('button', { name: 'Apply' }),
      ).not.toBeInTheDocument()
    },
  )

  it('does not offer Apply for projects in another course', async () => {
    // Students cannot apply across courses.
    server.use(
      http.get(`/api/projects/${project.id}`, () =>
        HttpResponse.json({ ...project, course_id: 'another-course' }),
      ),
    )
    await actAs(alice)
    renderApp(`/projects/${project.id}`)
    await screen.findByText('You can only apply to projects in your course.')
    expect(
      screen.queryByRole('button', { name: 'Apply' }),
    ).not.toBeInTheDocument()
  })

  it('does not offer Apply to a supervisor', async () => {
    // Apply belongs to students, while supervisors can still read the project.
    server.use(
      http.get(`/api/projects/${project.id}`, () => HttpResponse.json(project)),
    )
    await actAs(david)
    renderApp(`/projects/${project.id}`)
    await screen.findByRole('heading', { name: project.title })
    expect(
      screen.queryByRole('button', { name: 'Apply' }),
    ).not.toBeInTheDocument()
  })
})
