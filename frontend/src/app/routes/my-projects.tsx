import { PagePlaceholder } from '@/components/page-placeholder'

/**
 * Supervisors: their own projects, with slots used and applications waiting.
 * Each links to the project's page, where they accept or decline (#238).
 */
export function MyProjectsPage() {
  return <PagePlaceholder title="My projects" issue={238} />
}
