import { screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { http, HttpResponse } from 'msw'
import { describe, expect, it, vi } from 'vitest'
import { api } from '../../api/client'
import { actAs, getActingAs } from '../../auth/session'
import { alice, carol, david } from '../../test/fixtures'
import { renderApp } from '../../test/renderApp'
import { server } from '../../test/server'

// The side menu and the mobile drawer both have a switcher; the side menu's
// renders first.
async function openSwitcher() {
  const [combobox] = await screen.findAllByRole('combobox', {
    name: /acting as/i,
  })
  await waitFor(() => {
    expect(combobox).not.toHaveAttribute('aria-disabled')
  })
  await userEvent.click(combobox)
  return combobox
}

describe('UserSwitcher', () => {
  it('starts with nobody picked and lists users by role', async () => {
    renderApp('/projects')
    const combobox = await openSwitcher()
    expect(combobox).toHaveTextContent('Nobody')

    const listbox = screen.getByRole('listbox')
    expect(within(listbox).getByText('Students')).toBeInTheDocument()
    expect(within(listbox).getByText('Supervisors')).toBeInTheDocument()
    expect(within(listbox).getByText('Instructors')).toBeInTheDocument()
    // No TAs in the fixtures, so no empty TA heading.
    expect(within(listbox).queryByText('TAs')).not.toBeInTheDocument()
    expect(
      within(listbox).getByRole('option', { name: /Alice Anderson/ }),
    ).toBeInTheDocument()
  })

  it('signs in as the picked user and sends their token', async () => {
    renderApp('/projects')
    const combobox = await openSwitcher()
    await userEvent.click(screen.getByRole('option', { name: /David/ }))

    await waitFor(() => {
      expect(combobox).toHaveTextContent('David Supervisor')
    })
    expect(combobox).toHaveTextContent('Supervisor')
    expect(getActingAs()?.id).toBe(david.id)

    let authorization: string | null = null
    server.use(
      http.get('/api/health', ({ request }) => {
        authorization = request.headers.get('Authorization')
        return HttpResponse.json({ status: 'ok' })
      }),
    )
    await api.GET('/api/health')
    expect(authorization).toMatch(/^Bearer header\./)
  })

  it('saves the picked user so a reload keeps them', async () => {
    const first = renderApp('/projects')
    await openSwitcher()
    await userEvent.click(screen.getByRole('option', { name: /Carol/ }))
    await waitFor(() => {
      expect(getActingAs()?.id).toBe(carol.id)
    })
    first.unmount()

    expect(localStorage.getItem('keystone.actingAs')).toContain(carol.email)
  })

  it('keeps the current user and explains when sign-in fails', async () => {
    server.use(
      http.post('/auth/login', () =>
        HttpResponse.json({ detail: 'LOGIN_BAD_CREDENTIALS' }, { status: 400 }),
      ),
    )
    renderApp('/projects')
    const combobox = await openSwitcher()
    await userEvent.click(screen.getByRole('option', { name: /Alice/ }))

    const [alert] = await screen.findAllByRole('alert')
    expect(alert).toHaveTextContent(`Couldn't sign in as ${alice.email}`)
    expect(combobox).toHaveTextContent('Nobody')
    expect(getActingAs()).toBeNull()
  })

  it('says so when the users list fails to load', async () => {
    server.use(
      http.get('/api/users', () => HttpResponse.json(null, { status: 500 })),
    )
    renderApp('/projects')
    const [alert] = await screen.findAllByRole('alert')
    expect(alert).toHaveTextContent('Failed to load users')
  })

  it('shows the remembered user while the list loads, without MUI warnings', async () => {
    await actAs(alice)
    const consoleError = vi.spyOn(console, 'error')
    let release = () => {}
    const loaded = new Promise<void>((resolve) => {
      release = resolve
    })
    server.use(
      http.get('/api/users', async () => {
        await loaded
        return HttpResponse.json([alice, david])
      }),
    )
    renderApp('/projects')
    const [combobox] = await screen.findAllByRole('combobox', {
      name: /acting as/i,
    })
    expect(combobox).toHaveTextContent('Alice Anderson')

    release()
    await waitFor(() => {
      expect(combobox).not.toHaveAttribute('aria-disabled')
    })
    expect(combobox).toHaveTextContent('Alice Anderson')
    expect(consoleError.mock.calls.flat().join(' ')).not.toContain(
      'out-of-range',
    )
    consoleError.mockRestore()
  })

  it('signs out when Nobody is picked', async () => {
    renderApp('/projects')
    await openSwitcher()
    await userEvent.click(screen.getByRole('option', { name: /Alice/ }))
    await waitFor(() => {
      expect(getActingAs()?.id).toBe(alice.id)
    })

    await openSwitcher()
    await userEvent.click(screen.getByRole('option', { name: /Nobody/ }))
    await waitFor(() => {
      expect(getActingAs()).toBeNull()
    })
  })
})

describe('UserSwitcher after a reseed', () => {
  it('picks up the new id of a user with the same email', async () => {
    renderApp('/projects')
    await openSwitcher()
    await userEvent.click(screen.getByRole('option', { name: /Alice/ }))
    await waitFor(() => {
      expect(getActingAs()?.id).toBe(alice.id)
    })

    const reseeded = { ...alice, id: '00000000-0000-4000-8000-0000000000aa' }
    server.use(
      http.get('/api/users', () => HttpResponse.json([reseeded, david])),
    )
    // Switching to someone else and back is the simplest way to refetch.
    await openSwitcher()
    await userEvent.click(screen.getByRole('option', { name: /David/ }))
    await waitFor(() => {
      expect(getActingAs()?.id).toBe(david.id)
    })
    await openSwitcher()
    await userEvent.click(screen.getByRole('option', { name: /Alice/ }))
    await waitFor(() => {
      expect(getActingAs()?.id).toBe(reseeded.id)
    })
  })
})
