import { screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { delay, http, HttpResponse } from 'msw'
import { describe, expect, it } from 'vitest'
import { david } from '@/testing/mocks/fixtures'
import { course, project } from '@/testing/mocks/projects'
import { server } from '@/testing/mocks/server'
import { renderApp } from '@/testing/test-utils'

describe('project catalog', () => {
  it.each([
    { status: 'open', label: 'Open', reserved: 1, available: 1 },
    { status: 'full', label: 'Full', reserved: 2, available: 0 },
    { status: 'closed', label: 'Closed', reserved: 1, available: 1 },
  ] as const)(
    'displays $label projects and their slot counts',
    async ({ status, label, reserved, available }) => {
      // Each card shows the status and slot counts returned by the API.
      server.use(
        http.get('/api/projects', () =>
          HttpResponse.json([
            {
              ...project,
              status,
              slots_reserved: reserved,
              slots_available: available,
            },
          ]),
        ),
      )
      renderApp('/projects')
      await screen.findByRole('heading', { name: project.title })
      expect(screen.getByText(label)).toBeInTheDocument()
      expect(
        screen.getByText(
          `Capacity: ${reserved} of 2 slots reserved | Available: ${available}`,
        ),
      ).toBeInTheDocument()
    },
  )

  it('sends the Closed availability filter to the API', async () => {
    // Selecting Closed requests closed projects from the backend.
    const requests: URLSearchParams[] = []
    server.use(
      http.get('/api/projects', ({ request }) => {
        requests.push(new URL(request.url).searchParams)
        return HttpResponse.json([])
      }),
    )
    const user = userEvent.setup()
    renderApp('/projects')
    await screen.findByText('No projects match your filters.')
    await user.click(screen.getByRole('combobox', { name: 'Availability' }))
    await user.click(await screen.findByRole('option', { name: 'Closed' }))
    await waitFor(() => expect(requests.at(-1)?.get('status')).toBe('closed'))
  })

  it('displays project details and the details link', async () => {
    // The catalog card shows the API values and links to that project's URL.
    server.use(http.get('/api/projects', () => HttpResponse.json([project])))
    renderApp('/projects')

    expect(
      await screen.findByRole('heading', { name: project.title }),
    ).toBeInTheDocument()
    expect(screen.getByText(project.background)).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'View details' })).toHaveAttribute(
      'href',
      `/projects/${project.id}`,
    )
  })

  it('combines filters in API requests and clears them independently', async () => {
    // Selecting one filter keeps the other filters, and clearing restores the unfiltered request.
    const requests: URLSearchParams[] = []
    server.use(
      http.get('/api/courses', () => HttpResponse.json([course])),
      http.get('/api/projects', ({ request }) => {
        const query = new URL(request.url).searchParams
        requests.push(query)
        return HttpResponse.json(
          query.get('status') === 'full' ? [] : [project],
        )
      }),
    )
    const user = userEvent.setup()
    renderApp('/projects')
    await screen.findByRole('heading', { name: project.title })
    await waitFor(() =>
      expect(screen.getByRole('combobox', { name: 'Course' })).toBeEnabled(),
    )
    await waitFor(() =>
      expect(
        screen.getByRole('combobox', { name: 'Supervisor' }),
      ).toBeEnabled(),
    )

    await user.click(screen.getByRole('combobox', { name: 'Course' }))
    await user.click(
      await screen.findByRole('option', {
        name: `${course.code} - ${course.name}`,
      }),
    )
    await waitFor(() =>
      expect(requests.at(-1)?.get('course_id')).toBe(course.id),
    )

    await user.click(screen.getByRole('combobox', { name: 'Supervisor' }))
    await user.click(
      await screen.findByRole('option', { name: 'David Supervisor' }),
    )
    await waitFor(() =>
      expect(requests.at(-1)?.get('supervisor_id')).toBe(david.id),
    )

    await user.click(screen.getByRole('combobox', { name: 'Availability' }))
    await user.click(await screen.findByRole('option', { name: 'Full' }))
    await screen.findByText('No projects match your filters.')
    expect(Object.fromEntries(requests.at(-1) ?? [])).toEqual({
      course_id: course.id,
      supervisor_id: david.id,
      status: 'full',
    })

    await user.click(screen.getByRole('combobox', { name: 'Availability' }))
    await user.click(
      await screen.findByRole('option', { name: 'All projects' }),
    )
    await screen.findByRole('heading', { name: project.title })
    await user.click(screen.getByRole('combobox', { name: 'Course' }))
    await user.click(await screen.findByRole('option', { name: 'All courses' }))
    await waitFor(() => expect(requests.at(-1)?.has('course_id')).toBe(false))
    expect(requests.at(-1)?.get('supervisor_id')).toBe(david.id)
    await user.click(screen.getByRole('combobox', { name: 'Supervisor' }))
    await user.click(
      await screen.findByRole('option', { name: 'All supervisors' }),
    )
    await waitFor(() => expect(requests.at(-1)?.size).toBe(0))
  })

  it('shows loading before projects arrive', async () => {
    // A slow API response displays a loading indicator until the cards arrive.
    server.use(
      http.get('/api/projects', async () => {
        await delay(150)
        return HttpResponse.json([project])
      }),
    )
    renderApp('/projects')
    expect(
      screen.getByRole('progressbar', { name: 'Loading projects' }),
    ).toBeInTheDocument()
    await screen.findByRole('heading', { name: project.title })
    expect(
      screen.queryByRole('progressbar', { name: 'Loading projects' }),
    ).not.toBeInTheDocument()
  })

  it('shows an empty result message', async () => {
    // An empty API list produces a helpful message rather than empty cards.
    renderApp('/projects')
    expect(
      await screen.findByText('No projects match your filters.'),
    ).toBeInTheDocument()
  })

  it('allows retry after a failed project request', async () => {
    // Retry fetches the catalog again and replaces the error with project cards.
    let failed = true
    server.use(
      http.get('/api/projects', () =>
        failed
          ? HttpResponse.json({ detail: 'Unavailable' }, { status: 500 })
          : HttpResponse.json([project]),
      ),
    )
    const user = userEvent.setup()
    renderApp('/projects')
    const alert = await screen.findByRole('alert')
    expect(alert).toHaveTextContent('Could not load projects.')
    failed = false
    await user.click(within(alert).getByRole('button', { name: 'Retry' }))
    expect(
      await screen.findByRole('heading', { name: project.title }),
    ).toBeInTheDocument()
  })

  it('keeps projects visible when course options fail', async () => {
    // Failure to load filter options warns the user without hiding the catalog.
    server.use(
      http.get('/api/courses', () => HttpResponse.json({}, { status: 500 })),
      http.get('/api/projects', () => HttpResponse.json([project])),
    )
    renderApp('/projects')
    expect(
      await screen.findByRole('heading', { name: project.title }),
    ).toBeInTheDocument()
    expect(
      await screen.findByText('Some filter options could not be loaded.'),
    ).toBeInTheDocument()
    expect(screen.getByRole('combobox', { name: 'Course' })).toHaveAttribute(
      'aria-disabled',
      'true',
    )
  })
})
