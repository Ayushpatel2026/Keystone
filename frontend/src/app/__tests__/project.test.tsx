import { screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { delay, http, HttpResponse } from 'msw'
import { describe, expect, it } from 'vitest'
import { course, project } from '@/testing/mocks/projects'
import { server } from '@/testing/mocks/server'
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
