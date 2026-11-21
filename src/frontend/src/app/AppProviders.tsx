import type {} from '@mui/x-charts/themeAugmentation'
import type {} from '@mui/x-data-grid/themeAugmentation'
import type {} from '@mui/x-date-pickers/themeAugmentation'
import type {} from '@mui/x-tree-view/themeAugmentation'
import CssBaseline from '@mui/material/CssBaseline'
import { QueryClientProvider, type QueryClient } from '@tanstack/react-query'
import { queryClient as defaultQueryClient } from '../api/queryClient'
import AppTheme from '../theme/AppTheme'
import {
  chartsCustomizations,
  dataGridCustomizations,
  datePickersCustomizations,
  treeViewCustomizations,
} from '../theme/customizations/x'

// Styling for the MUI X components (charts, data grid, date pickers, tree
// view), on top of the core component styling AppTheme already applies.
const muiXCustomizations = {
  ...chartsCustomizations,
  ...dataGridCustomizations,
  ...datePickersCustomizations,
  ...treeViewCustomizations,
}

interface AppProvidersProps {
  children: React.ReactNode
  /** Tests pass a fresh client so cached data doesn't leak between them. */
  queryClient?: QueryClient
}

/** Everything the app needs around it: data cache, theme, base styles. */
export function AppProviders({
  children,
  queryClient = defaultQueryClient,
}: AppProvidersProps) {
  return (
    <QueryClientProvider client={queryClient}>
      <AppTheme themeComponents={muiXCustomizations}>
        <CssBaseline enableColorScheme />
        {children}
      </AppTheme>
    </QueryClientProvider>
  )
}
