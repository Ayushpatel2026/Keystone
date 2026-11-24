import { type RouteObject } from 'react-router'
import { courseStaff } from '@/lib/authorization'
import { MyProjectsPage } from '@/app/routes/my-projects'
import { ProjectCatalogPage } from '@/app/routes/projects'
import { ProjectDetailPage } from '@/app/routes/project'
import { MyTeamPage } from '@/app/routes/my-team'
import { TeamsPage } from '@/app/routes/teams'
import { HomePage } from '@/app/routes/home'
import { AppLayout } from '@/components/layouts/app-layout'
import { NotFoundPage } from '@/app/routes/not-found'
import { RequireRole } from '@/components/require-role'

/**
 * The route table. Every page renders inside AppLayout.
 * Paths here must match the ones in `@/config/paths`.
 *
 * Pages for one role are wrapped in RequireRole. Pages for everyone, like a
 * project, show each role its own actions instead.
 */
export const routes: RouteObject[] = [
  {
    path: '/',
    element: <AppLayout />,
    children: [
      { index: true, element: <HomePage /> },
      { path: 'projects', element: <ProjectCatalogPage /> },
      { path: 'projects/:projectId', element: <ProjectDetailPage /> },
      {
        path: 'team',
        element: (
          <RequireRole roles={['student']} title="My team">
            <MyTeamPage />
          </RequireRole>
        ),
      },
      {
        path: 'my-projects',
        element: (
          <RequireRole roles={['supervisor']} title="My projects">
            <MyProjectsPage />
          </RequireRole>
        ),
      },
      {
        path: 'teams',
        element: (
          <RequireRole roles={courseStaff} title="Teams">
            <TeamsPage />
          </RequireRole>
        ),
      },
      { path: '*', element: <NotFoundPage /> },
    ],
  },
]
