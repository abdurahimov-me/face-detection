import { createRootRoute, createRoute, createRouter } from '@tanstack/react-router'
import { AppShell } from './components/AppShell'
import { DashboardPage } from './pages/DashboardPage'
import { EnrollPage } from './pages/EnrollPage'
import { TestPage } from './pages/TestPage'
import { VideoPage } from './pages/VideoPage'

const rootRoute = createRootRoute({ component: AppShell })
const dashboardRoute = createRoute({ getParentRoute: () => rootRoute, path: '/', component: DashboardPage })
const enrollRoute = createRoute({ getParentRoute: () => rootRoute, path: '/enroll', component: EnrollPage })
const testRoute = createRoute({ getParentRoute: () => rootRoute, path: '/test', component: TestPage })
const videoRoute = createRoute({ getParentRoute: () => rootRoute, path: '/video', component: VideoPage })

const routeTree = rootRoute.addChildren([dashboardRoute, enrollRoute, testRoute, videoRoute])
export const router = createRouter({ routeTree })

declare module '@tanstack/react-router' {
  interface Register {
    router: typeof router
  }
}
