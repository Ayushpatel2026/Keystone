// Inter, bundled with the app (no Google Fonts request). The opsz variant
// also adjusts letter shapes for large headings and small text.
import '@fontsource-variable/inter/opsz.css'
import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { App } from '@/app'

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <App />
  </StrictMode>,
)
