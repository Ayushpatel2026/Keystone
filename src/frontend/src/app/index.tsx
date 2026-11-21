import { createBrowserRouter, RouterProvider } from 'react-router'
import { AppProvider } from '@/app/provider'
import { routes } from '@/app/router'

const router = createBrowserRouter(routes)

/** The whole app: providers around the router. */
export function App() {
  return (
    <AppProvider>
      <RouterProvider router={router} />
    </AppProvider>
  )
}
