import Button from '@mui/material/Button'
import { Link } from 'react-router'
import { PagePlaceholder } from '@/components/page-placeholder'
import { paths } from '@/config/paths'

export function NotFoundPage() {
  return (
    <PagePlaceholder title="Page not found">
      <Button component={Link} to={paths.home} sx={{ alignSelf: 'start' }}>
        Go to your home page
      </Button>
    </PagePlaceholder>
  )
}
