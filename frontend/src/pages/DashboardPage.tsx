import { Link } from '@tanstack/react-router'
import { ArrowRight, ScanFace, ShieldCheck, UserPlus, Users } from 'lucide-react'
import { UsersTable } from '../components/UsersTable'
import { useFaceUsers } from '../lib/queries'

export function DashboardPage() {
  const users = useFaceUsers()
  return (
    <>
      <section className="hero-grid">
        <div><p className="eyebrow">Biometrik boshqaruv</p><h1>Yuzlarni boshqarish,<br /><span>aniq va tez.</span></h1><p className="hero-copy">Kamera orqali yangi foydalanuvchi qo‘shing yoki real vaqt rejimida tanib ko‘ring.</p></div>
        <div className="hero-actions"><Link to="/enroll" className="button-primary"><UserPlus size={19} /> User qo‘shish <ArrowRight size={17} /></Link><Link to="/test" className="button-secondary"><ScanFace size={19} /> Kamerada test</Link></div>
      </section>
      <section className="stats-grid">
        <div className="stat-card"><span className="stat-icon"><Users /></span><div><small>Jami userlar</small><strong>{users.data?.length ?? '—'}</strong></div></div>
        <div className="stat-card"><span className="stat-icon"><ScanFace /></span><div><small>Recognition modeli</small><strong>ArcFace</strong></div></div>
        <div className="stat-card"><span className="stat-icon"><ShieldCheck /></span><div><small>Vector storage</small><strong>Qdrant</strong></div></div>
      </section>
      <UsersTable />
    </>
  )
}
