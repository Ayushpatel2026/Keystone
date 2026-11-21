import { screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it } from 'vitest'
import { actAs } from '@/lib/auth'
import { alice, carol, david } from '@/testing/mocks/fixtures'
import { renderApp } from '@/testing/test-utils'

/** The link labels in the side menu's main section, top to bottom. */
function menuLinks() {
  const [nav] = screen.getAllByRole('navigation', { name: 'Main' })
  return within(nav)
    .getAllByRole('link')
    .map((link) => link.textContent)
}

describe('home page', () => {
  it('asks who to act as when nobody is picked', async () => {
    const { router } = renderApp('/')

    expect(
      await screen.findByRole('heading', { name: 'Welcome to Keystone' }),
    ).toBeInTheDocument()
    expect(router.state.location.pathname).toBe('/')
  })

  it.each([
    ['student', alice, '/projects', 'Projects'],
    ['supervisor', david, '/my-projects', 'My projects'],
    ['instructor', carol, '/teams', 'Teams'],
  ])('sends a %s to their home page', async (_role, user, path, heading) => {
    await actAs(user)
    const { router } = renderApp('/')

    expect(
      await screen.findByRole('heading', { name: heading }),
    ).toBeInTheDocument()
    expect(router.state.location.pathname).toBe(path)
  })
})

describe('menu', () => {
  it.each([
    ['nobody', null, ['Demo']],
    ['a student', alice, ['Projects', 'My team', 'Demo']],
    ['a supervisor', david, ['My projects', 'Projects', 'Demo']],
    ['an instructor', carol, ['Teams', 'Projects', 'Demo']],
  ])('shows %s their own pages', async (_who, user, links) => {
    if (user) await actAs(user)
    renderApp('/demo')
    await screen.findByRole('heading', { name: 'Demo' })

    expect(menuLinks()).toEqual(links)
  })

  it('navigates with the menu links', async () => {
    await actAs(alice)
    const { router } = renderApp('/projects')

    const [nav] = screen.getAllByRole('navigation', { name: 'Main' })
    await userEvent.click(within(nav).getByRole('link', { name: 'My team' }))

    expect(
      await screen.findByRole('heading', { name: 'My team' }),
    ).toBeInTheDocument()
    expect(router.state.location.pathname).toBe('/team')
  })
})

describe('role-only pages', () => {
  it("explains who a page is for when the role doesn't match", async () => {
    await actAs(alice)
    renderApp('/teams')

    expect(
      await screen.findByText(/This page is for course staff/),
    ).toBeInTheDocument()
    expect(
      screen.getByText(/acting as Alice Anderson, a student/),
    ).toBeInTheDocument()
    expect(
      screen.getByRole('link', { name: 'Go to your home page' }),
    ).toHaveAttribute('href', '/projects')
  })

  it('asks who to act as when nobody is picked', async () => {
    renderApp('/my-projects')

    expect(
      await screen.findByText(/This page is for supervisors/),
    ).toBeInTheDocument()
    expect(
      screen.getByText(/haven't picked anyone to act as/),
    ).toBeInTheDocument()
  })
})

describe('shared pages', () => {
  it('passes the URL parameter to the project page', async () => {
    renderApp('/projects/abc-123')

    expect(
      await screen.findByRole('heading', { name: 'Project abc-123' }),
    ).toBeInTheDocument()
  })

  it('shows a not-found page for unknown URLs', async () => {
    renderApp('/no/such/page')

    expect(
      await screen.findByRole('heading', { name: 'Page not found' }),
    ).toBeInTheDocument()
  })
})
