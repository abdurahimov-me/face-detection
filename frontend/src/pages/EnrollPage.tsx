import { useNavigate } from '@tanstack/react-router'
import { CameraIcon, CheckCircle2, ScanFace } from 'lucide-react'
import { FormEvent, useRef, useState } from 'react'
import { Camera, type CameraHandle } from '../components/Camera'
import { useEnrollFace } from '../lib/queries'

export function EnrollPage() {
  const camera = useRef<CameraHandle>(null)
  const enroll = useEnrollFace()
  const navigate = useNavigate()
  const [userId, setUserId] = useState('')
  const [fullName, setFullName] = useState('')
  const [snapshot, setSnapshot] = useState<Blob | null>(null)
  const [preview, setPreview] = useState<string | null>(null)

  async function capture() {
    const blob = await camera.current?.capture()
    if (!blob) return
    if (preview) URL.revokeObjectURL(preview)
    setSnapshot(blob)
    setPreview(URL.createObjectURL(blob))
  }

  async function submit(event: FormEvent) {
    event.preventDefault()
    if (!snapshot) return
    try {
      await enroll.mutateAsync({ userId, fullName, image: snapshot })
      await navigate({ to: '/' })
    } catch {
      // React Query exposes the server validation message in the form.
    }
  }

  return (
    <section>
      <div className="page-title"><div><p className="eyebrow">Enrollment</p><h1>Yangi user qo‘shish</h1><p>Yuz kameraga to‘g‘ri qaragan va yorug‘lik yetarli bo‘lsin.</p></div></div>
      <div className="work-grid">
        <div className="panel p-3">
          <Camera ref={camera}>{preview && <img src={preview} className="camera-preview absolute inset-0 h-full w-full object-cover" alt="Olingan surat" />}<div className="face-guide"><span /><span /><span /><span /></div></Camera>
          <div className="camera-toolbar"><div><ScanFace size={17} /><span>{snapshot ? 'Kadr tayyor' : 'Yuzni markazga joylang'}</span></div><button className="button-secondary" type="button" onClick={() => void capture()}><CameraIcon size={17} /> {snapshot ? 'Qayta olish' : 'Suratga olish'}</button></div>
        </div>
        <form className="panel form-panel" onSubmit={(e) => void submit(e)}>
          <div><p className="eyebrow">Foydalanuvchi</p><h2>Asosiy ma’lumotlar</h2></div>
          <label className="field"><span>User ID</span><input value={userId} onChange={(e) => setUserId(e.target.value)} placeholder="Masalan: 8853120" required /></label>
          <label className="field"><span>To‘liq ism</span><input value={fullName} onChange={(e) => setFullName(e.target.value)} placeholder="Ism Familiya" required /></label>
          <div className="quality-note"><CheckCircle2 size={19} /><div><strong>Bitta yuz talab qilinadi</strong><small>Server surat sifatini va yuzlar sonini tekshiradi.</small></div></div>
          {enroll.isError && <p className="error-box">{enroll.error.message}</p>}
          <button className="button-primary mt-auto justify-center" disabled={!snapshot || enroll.isPending}>{enroll.isPending ? 'Saqlanmoqda…' : 'Userni bazaga qo‘shish'}</button>
        </form>
      </div>
    </section>
  )
}
