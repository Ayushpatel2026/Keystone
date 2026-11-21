import { useParams } from 'react-router'
import { PagePlaceholder } from '../../../components/PagePlaceholder'

/** One project's details, and applying to it. */
export function ProjectDetailPage() {
  const { projectId } = useParams()
  return <PagePlaceholder title={`Project ${projectId ?? ''}`} issue={236} />
}
