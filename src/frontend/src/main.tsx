// Inter, bundled with the app (no Google Fonts request). The opsz variant
// also adjusts letter shapes for large headings and small text.
import '@fontsource-variable/inter/opsz.css'
import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { createBrowserRouter, RouterProvider } from 'react-router'
import { AppProviders } from './app/AppProviders.tsx'
import { routes } from './app/routes.tsx'

const router = createBrowserRouter(routes)

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <AppProviders>
      <RouterProvider router={router} />
    </AppProviders>
  </StrictMode>,
)
