import { Link } from '@tanstack/react-router'
import { ArrowRight, Film, ScanFace, UserPlus, Users } from 'lucide-react'
import { UsersTable } from '../components/UsersTable'
import { useFaceUsers } from '../lib/queries'

export function DashboardPage() {
  const users = useFaceUsers()
  return (
    <>
      <section className="hero-grid">
        <div><p className="eyebrow">Foydalanuvchilar</p><h1>Yuzlarni qo‘shing<br /><span>va tekshiring.</span></h1><p className="hero-copy">Yangi foydalanuvchini kameradan qo‘shing yoki ro‘yxatda borligini tekshiring.</p></div>
        <div className="hero-actions"><Link to="/enroll" className="button-primary"><UserPlus size={19} /> Foydalanuvchi qo‘shish <ArrowRight size={17} /></Link><Link to="/test" className="button-secondary"><ScanFace size={19} /> Kamerada tekshirish</Link></div>
      </section>
      <section className="stats-grid">
        <div className="stat-card"><span className="stat-icon"><Users /></span><div><small>Jami foydalanuvchilar</small><strong>{users.data?.length ?? '—'}</strong></div></div>
        <div className="stat-card"><span className="stat-icon"><ScanFace /></span><div><small>Kamerada tekshirish</small><strong>Tayyor</strong></div></div>
        <div className="stat-card"><span className="stat-icon"><Film /></span><div><small>Video tahlili</small><strong>Tayyor</strong></div></div>
      </section>
      <UsersTable />
    </>
  )
}
