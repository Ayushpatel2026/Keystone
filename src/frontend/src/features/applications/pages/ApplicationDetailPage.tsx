import { useParams } from 'react-router'
import { PagePlaceholder } from '../../../components/PagePlaceholder'

/** One application: its status history and the actions available now. */
export function ApplicationDetailPage() {
  const { applicationId } = useParams()
  return (
    <PagePlaceholder title={`Application ${applicationId ?? ''}`} issue={239} />
  )
}
