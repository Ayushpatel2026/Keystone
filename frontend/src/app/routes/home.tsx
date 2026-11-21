import Stack from '@mui/material/Stack'
import Typography from '@mui/material/Typography'
import { Navigate } from 'react-router'
import { useActingAs } from '@/lib/auth'
import { homePath } from '@/components/layouts/nav-items'

/**
 * `/`: sends each role to its own home page, or asks who to act as.
 *
 * Later this can become every user's checklist of required actions (SRS
 * UC_NotifyChecklist).
 */
export function HomePage() {
  const actingAs = useActingAs()
  if (actingAs) return <Navigate to={homePath(actingAs.role)} replace />

  return (
    <Stack spacing={2}>
      <Typography variant="h4" component="h1">
        Welcome to Keystone
      </Typography>
      <Typography>
        Pick who to act as in <strong>Acting as</strong>, in the menu. Each role
        (student, supervisor, instructor, TA) sees its own pages.
      </Typography>
    </Stack>
  )
}
