import { Navigate, type RouteObject } from 'react-router'
import { ApplicationDetailPage } from '../features/applications/pages/ApplicationDetailPage'
import { ApplicationsPage } from '../features/applications/pages/ApplicationsPage'
import { DemoPage } from '../features/demo/pages/DemoPage'
import { ProjectCatalogPage } from '../features/projects/pages/ProjectCatalogPage'
import { ProjectDetailPage } from '../features/projects/pages/ProjectDetailPage'
import { InstructorReviewPage } from '../features/review/pages/InstructorReviewPage'
import { SupervisorApplicationsPage } from '../features/supervisor/pages/SupervisorApplicationsPage'
import { AppLayout } from './layout/AppLayout'
import { NotFoundPage } from './NotFoundPage'

/**
 * The route table. Every page renders inside AppLayout.
 * Paths here must match the ones in paths.ts.
 */
export const routes: RouteObject[] = [
  {
    path: '/',
    element: <AppLayout />,
    children: [
      { index: true, element: <Navigate to="/projects" replace /> },
      { path: 'projects', element: <ProjectCatalogPage /> },
      { path: 'projects/:projectId', element: <ProjectDetailPage /> },
      { path: 'applications', element: <ApplicationsPage /> },
      {
        path: 'applications/:applicationId',
        element: <ApplicationDetailPage />,
      },
      {
        path: 'supervisor/applications',
        element: <SupervisorApplicationsPage />,
      },
      { path: 'instructor/review', element: <InstructorReviewPage /> },
      { path: 'demo', element: <DemoPage /> },
      { path: '*', element: <NotFoundPage /> },
    ],
  },
]
