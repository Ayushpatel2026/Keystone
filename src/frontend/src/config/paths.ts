/**
 * Every URL in the app, in one place.
 *
 * Link with these instead of typing strings, so renaming a route is a
 * one-line change:
 *   <Link to={paths.projectDetail(project.id)}>...</Link>
 *
 * URLs name things (a project, a team), not roles. A page shows what the
 * current user's role can do there, so the same link works for everyone.
 *
 * When adding a route, add its path here and its route in `src/app/router.tsx`.
 */
export const paths = {
  home: '/',
  projects: '/projects',
  projectDetail: (projectId: string) => `/projects/${projectId}`,
  myTeam: '/team',
  myProjects: '/my-projects',
  teams: '/teams',
  demo: '/demo',
} as const
