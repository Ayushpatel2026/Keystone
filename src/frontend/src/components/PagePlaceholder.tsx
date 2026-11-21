import Stack from '@mui/material/Stack'
import Typography from '@mui/material/Typography'

interface PagePlaceholderProps {
  title: string
  /** GitHub issue that will build this page. */
  issue?: number
  children?: React.ReactNode
}

/**
 * Stand-in for a page that hasn't been built yet. Replace it with the real
 * page content when working on the issue.
 */
export function PagePlaceholder({
  title,
  issue,
  children,
}: PagePlaceholderProps) {
  return (
    <Stack spacing={2}>
      <Typography variant="h4" component="h1">
        {title}
      </Typography>
      <Typography color="text.secondary">
        Not built yet{issue !== undefined ? ` (issue #${String(issue)})` : ''}.
      </Typography>
      {children}
    </Stack>
  )
}
