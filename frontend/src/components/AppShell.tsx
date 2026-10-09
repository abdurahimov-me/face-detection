import { Link, Outlet, useRouterState } from '@tanstack/react-router'
import { Film, ScanFace, UserPlus, Users } from 'lucide-react'

export function AppShell() {
  const path = useRouterState({ select: (state) => state.location.pathname })

  return (
    <div className="min-h-screen">
      <header className="topbar">
        <Link to="/" className="brand">
          <span className="brand-mark"><ScanFace size={23} /></span>
          <span>
            <strong>Yuz nazorati</strong>
            <small>Foydalanuvchilar</small>
          </span>
        </Link>
        <nav className="nav-pills">
          <Link to="/" className={path === '/' ? 'active' : ''}><Users size={17} /> Foydalanuvchilar</Link>
          <Link to="/enroll" className={path === '/enroll' ? 'active' : ''}><UserPlus size={17} /> Qo‘shish</Link>
          <Link to="/test" className={path === '/test' ? 'active' : ''}><ScanFace size={17} /> Tekshirish</Link>
          <Link to="/video" className={path === '/video' ? 'active' : ''}><Film size={17} /> Video</Link>
        </nav>
        <div className="status-pill"><span /> Modul faol</div>
      </header>
      <main className="page"><Outlet /></main>
    </div>
  )
}
