import { Search, Trash2, UserRound } from 'lucide-react'
import { useMemo, useState } from 'react'
import { useDeleteFaceUser, useFaceUsers } from '../lib/queries'

export function UsersTable() {
  const users = useFaceUsers()
  const removeUser = useDeleteFaceUser()
  const [search, setSearch] = useState('')
  const filtered = useMemo(() => {
    const value = search.trim().toLowerCase()
    return (users.data ?? []).filter(
      (user) => !value || user.full_name.toLowerCase().includes(value) || user.user_id.toLowerCase().includes(value),
    )
  }, [search, users.data])

  return (
    <section className="panel overflow-hidden">
      <div className="panel-heading">
        <div><p className="eyebrow">Ro‘yxat</p><h2>Foydalanuvchilar</h2></div>
        <label className="search-box"><Search size={17} /><input value={search} onChange={(e) => setSearch(e.target.value)} placeholder="Ism yoki ID bo‘yicha…" /></label>
      </div>
      {users.isError ? (
        <div className="empty-state"><p>Ro‘yxatni yuklab bo‘lmadi.</p><small>{users.error.message}</small><button className="button-secondary" onClick={() => void users.refetch()}>Qayta urinish</button></div>
      ) : users.isLoading ? (
        <div className="empty-state">Foydalanuvchilar yuklanmoqda…</div>
      ) : filtered.length === 0 ? (
        <div className="empty-state"><UserRound size={34} /><p>Hozircha foydalanuvchilar yo‘q</p><small>Birinchi foydalanuvchini kamera orqali qo‘shing.</small></div>
      ) : (
        <div className="overflow-x-auto">
          <table>
            <thead><tr><th>Foydalanuvchi</th><th>ID</th><th>Qo‘shilgan vaqt</th><th>Holat</th><th /></tr></thead>
            <tbody>{filtered.map((user) => (
              <tr key={user.user_id}>
                <td><div className="user-cell"><span className="avatar">{user.image_url ? <img src={user.image_url} alt="" /> : user.full_name.slice(0, 1).toUpperCase()}</span><strong>{user.full_name}</strong></div></td>
                <td><code>{user.user_id}</code></td>
                <td>{user.created_at ? new Date(user.created_at).toLocaleString('uz-UZ') : '—'}</td>
                <td><span className="badge-success">Faol</span></td>
                <td className="text-right"><button className="icon-button danger" disabled={removeUser.isPending} onClick={() => removeUser.mutate(user.user_id)} aria-label="O‘chirish"><Trash2 size={17} /></button></td>
              </tr>
            ))}</tbody>
          </table>
        </div>
      )}
    </section>
  )
}
