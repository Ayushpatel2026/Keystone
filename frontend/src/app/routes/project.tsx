import { useParams } from 'react-router'
import { PagePlaceholder } from '@/components/page-placeholder'

/**
 * One project, for every role. Students apply here (#236). The project's
 * supervisor sees its applications, with accept and decline (#238). Course
 * staff see its slots and every application's status.
 */
export function ProjectDetailPage() {
  const { projectId } = useParams()
  return <PagePlaceholder title={`Project ${projectId ?? ''}`} issue={236} />
}
