import Button from '@mui/material/Button'
import { Link } from 'react-router'
import { PagePlaceholder } from '../components/PagePlaceholder'
import { paths } from './paths'

export function NotFoundPage() {
  return (
    <PagePlaceholder title="Page not found">
      <Button component={Link} to={paths.projects} sx={{ alignSelf: 'start' }}>
        Go to projects
      </Button>
    </PagePlaceholder>
  )
}
