import { Link, Outlet, useRouterState } from '@tanstack/react-router'
import { ScanFace, UserPlus, Users } from 'lucide-react'

export function AppShell() {
  const path = useRouterState({ select: (state) => state.location.pathname })

  return (
    <div className="min-h-screen">
      <header className="topbar">
        <Link to="/" className="brand">
          <span className="brand-mark"><ScanFace size={23} /></span>
          <span>
            <strong>Face Console</strong>
            <small>Identity workspace</small>
          </span>
        </Link>
        <nav className="nav-pills">
          <Link to="/" className={path === '/' ? 'active' : ''}><Users size={17} /> Userlar</Link>
          <Link to="/enroll" className={path === '/enroll' ? 'active' : ''}><UserPlus size={17} /> Qo‘shish</Link>
          <Link to="/test" className={path === '/test' ? 'active' : ''}><ScanFace size={17} /> Test</Link>
        </nav>
        <div className="status-pill"><span /> Tizim faol</div>
      </header>
      <main className="page"><Outlet /></main>
    </div>
  )
}
