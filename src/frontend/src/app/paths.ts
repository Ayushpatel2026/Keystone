/**
 * Every URL in the app, in one place.
 *
 * Link with these instead of typing strings, so renaming a route is a
 * one-line change:
 *   <Link to={paths.projectDetail(project.id)}>...</Link>
 *
 * When adding a route, add its path here and its page in router.tsx.
 */
export const paths = {
  home: '/',
  projects: '/projects',
  projectDetail: (projectId: string) => `/projects/${projectId}`,
  applications: '/applications',
  applicationDetail: (applicationId: string) =>
    `/applications/${applicationId}`,
  supervisorApplications: '/supervisor/applications',
  instructorReview: '/instructor/review',
  demo: '/demo',
} as const
