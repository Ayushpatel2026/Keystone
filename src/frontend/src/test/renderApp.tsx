import { QueryClient } from '@tanstack/react-query'
import { render } from '@testing-library/react'
import { createMemoryRouter, RouterProvider } from 'react-router'
import { AppProviders } from '../app/AppProviders'
import { routes } from '../app/routes'

/**
 * Render the whole app at a URL, with fresh providers, for page tests:
 *   renderApp('/projects/123')
 */
export function renderApp(url: string) {
  const router = createMemoryRouter(routes, { initialEntries: [url] })
  // No retries, so a failed request shows its error right away in tests.
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  })

  return {
    router,
    ...render(
      <AppProviders queryClient={queryClient}>
        <RouterProvider router={router} />
      </AppProviders>,
    ),
  }
}
