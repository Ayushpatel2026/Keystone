import { screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it } from 'vitest'
import { renderApp } from '../test/renderApp'

describe('routes', () => {
  it('redirects the home page to the project catalog', async () => {
    const { router } = renderApp('/')

    expect(
      await screen.findByRole('heading', { name: 'Projects' }),
    ).toBeInTheDocument()
    expect(router.state.location.pathname).toBe('/projects')
  })

  it('passes the URL parameter to the detail page', async () => {
    renderApp('/projects/abc-123')

    expect(
      await screen.findByRole('heading', { name: 'Project abc-123' }),
    ).toBeInTheDocument()
  })

  it('navigates with the top bar links', async () => {
    const user = userEvent.setup()
    const { router } = renderApp('/projects')

    await user.click(screen.getByRole('link', { name: 'Instructor review' }))

    expect(
      await screen.findByRole('heading', { name: 'Instructor review' }),
    ).toBeInTheDocument()
    expect(router.state.location.pathname).toBe('/instructor/review')
  })

  it('shows a not-found page for unknown URLs', async () => {
    renderApp('/no/such/page')

    expect(
      await screen.findByRole('heading', { name: 'Page not found' }),
    ).toBeInTheDocument()
  })
})
