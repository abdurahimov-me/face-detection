import { useNavigate } from '@tanstack/react-router'
import { useQueryClient } from '@tanstack/react-query'
import { CheckCircle2, ImagePlus, ScanFace, Upload } from 'lucide-react'
import { type ChangeEvent, type FormEvent, useEffect, useRef, useState } from 'react'
import { Camera, type CameraHandle } from '../components/Camera'
import { createEnrollmentAnswer } from '../lib/api'
import { faceUsersQueryKey, useEnrollFace } from '../lib/queries'

const TOTAL_SAMPLES = 3
const MAX_IMAGE_BYTES = 8 * 1024 * 1024
const IMAGE_TYPES = new Set(['image/jpeg', 'image/png', 'image/webp'])

type EnrollmentMessage = {
  event: 'progress' | 'saving' | 'complete' | 'error'
  message: string
  collected: number
  total: number
}

async function waitForIceGathering(peer: RTCPeerConnection): Promise<void> {
  if (peer.iceGatheringState === 'complete') return
  await new Promise<void>((resolve, reject) => {
    const timeout = window.setTimeout(() => {
      peer.removeEventListener('icegatheringstatechange', listener)
      reject(new Error('Kamera bilan aloqa o‘rnatilmadi.'))
    }, 10000)
    const listener = () => {
      if (peer.iceGatheringState === 'complete') {
        window.clearTimeout(timeout)
        peer.removeEventListener('icegatheringstatechange', listener)
        resolve()
      }
    }
    peer.addEventListener('icegatheringstatechange', listener)
  })
}

export function EnrollPage() {
  const camera = useRef<CameraHandle>(null)
  const peer = useRef<RTCPeerConnection | null>(null)
  const queryClient = useQueryClient()
  const upload = useEnrollFace()
  const navigate = useNavigate()
  const [mode, setMode] = useState<'camera' | 'image'>('image')
  const [userId, setUserId] = useState('')
  const [fullName, setFullName] = useState('')
  const [image, setImage] = useState<File | null>(null)
  const [previewUrl, setPreviewUrl] = useState<string | null>(null)
  const [ready, setReady] = useState(false)
  const [busy, setBusy] = useState(false)
  const [collected, setCollected] = useState(0)
  const [message, setMessage] = useState('Kameraga qarang va boshlash tugmasini bosing.')
  const [error, setError] = useState<string | null>(null)
  const submitting = busy || upload.isPending

  useEffect(() => () => peer.current?.close(), [])
  useEffect(() => {
    if (!image) {
      setPreviewUrl(null)
      return
    }
    const url = URL.createObjectURL(image)
    setPreviewUrl(url)
    return () => URL.revokeObjectURL(url)
  }, [image])

  function selectMode(nextMode: 'camera' | 'image') {
    if (submitting || nextMode === mode) return
    peer.current?.close()
    setReady(false)
    setError(null)
    setMode(nextMode)
  }

  function selectImage(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0] ?? null
    setError(null)
    setImage(null)
    if (!file) return
    if (!IMAGE_TYPES.has(file.type)) {
      setError('Faqat JPEG, PNG yoki WebP rasm yuklang.')
      event.target.value = ''
      return
    }
    if (file.size > MAX_IMAGE_BYTES) {
      setError('Rasm hajmi 8 MB dan oshmasin.')
      event.target.value = ''
      return
    }
    setImage(file)
  }

  async function submit(event: FormEvent) {
    event.preventDefault()
    if (submitting) return
    setError(null)

    if (mode === 'image') {
      if (!image) {
        setError('Avval rasm tanlang.')
        return
      }
      try {
        await upload.mutateAsync({ userId: userId.trim(), fullName: fullName.trim(), image })
        await navigate({ to: '/' })
      } catch (cause) {
        setError(cause instanceof Error ? cause.message : 'Rasmni yuklashda xatolik yuz berdi.')
      }
      return
    }

    const video = camera.current?.video
    const stream = video?.srcObject as MediaStream | null
    const track = stream?.getVideoTracks()[0]
    if (!track) return

    peer.current?.close()
    const connection = new RTCPeerConnection()
    peer.current = connection
    setBusy(true)
    setCollected(0)
    setMessage('Kamera tayyorlanmoqda…')
    const channel = connection.createDataChannel('enrollment')
    channel.onopen = () => setMessage('Yuz kutilmoqda…')
    channel.onmessage = (incoming) => {
      const result = JSON.parse(incoming.data) as EnrollmentMessage
      setCollected(result.collected)
      setMessage(result.message)
      if (result.event === 'error') {
        setError(result.message)
        setBusy(false)
        connection.close()
      } else if (result.event === 'complete') {
        setBusy(false)
        connection.close()
        void queryClient.invalidateQueries({ queryKey: faceUsersQueryKey })
        void navigate({ to: '/' })
      }
    }
    connection.onconnectionstatechange = () => {
      if (connection.connectionState === 'failed') {
        setError('Kamera bilan aloqa uzildi. Qayta urinib ko‘ring.')
        setBusy(false)
      }
    }
    connection.addTrack(track, stream!)

    try {
      await connection.setLocalDescription(await connection.createOffer())
      await waitForIceGathering(connection)
      const answer = await createEnrollmentAnswer(
        connection.localDescription!, userId.trim(), fullName.trim(),
      )
      await connection.setRemoteDescription(answer)
    } catch (cause) {
      connection.close()
      setBusy(false)
      setError(cause instanceof Error ? cause.message : 'Ulanishda xatolik yuz berdi.')
    }
  }

  return (
    <section>
      <div className="page-title"><div><p className="eyebrow">Yangi foydalanuvchi</p><h1>Foydalanuvchi qo‘shish</h1><p>Kamera orqali yoki tayyor rasm yuklab foydalanuvchi qo‘shing.</p></div></div>
      <div className="enroll-mode-tabs" role="group" aria-label="Qo‘shish usuli">
        <button type="button" className={mode === 'camera' ? 'active' : ''} onClick={() => selectMode('camera')} disabled={submitting}><ScanFace size={17} /> Kamera orqali</button>
        <button type="button" className={mode === 'image' ? 'active' : ''} onClick={() => selectMode('image')} disabled={submitting}><ImagePlus size={17} /> Rasm faylini yuklash</button>
      </div>
      <div className="work-grid">
        <div className="panel p-3">
          {mode === 'camera' ? (
            <>
              <Camera ref={camera} onReady={() => setReady(true)}><div className="face-guide"><span /><span /><span /><span /></div></Camera>
              <div className="camera-toolbar"><div><ScanFace size={17} /><span>{message}</span></div><span>{collected} / {TOTAL_SAMPLES}</span></div>
            </>
          ) : (
            <>
              <label className={`image-upload-zone${previewUrl ? ' has-image' : ''}`}>
                <input type="file" accept="image/jpeg,image/png,image/webp" onChange={selectImage} disabled={submitting} aria-label="Yuz rasmini tanlash" />
                {previewUrl ? <img src={previewUrl} alt="Tanlangan yuz rasmi" /> : <span className="image-upload-empty"><ImagePlus size={36} /><strong>Kompyuterdan rasm faylini tanlang</strong><small>JPEG, PNG yoki WebP · 8 MB gacha</small></span>}
              </label>
              <div className="camera-toolbar"><div><ImagePlus size={17} /><span>{image?.name ?? 'Yuz aniq ko‘rinadigan rasmni tanlang.'}</span></div>{image && <span>Almashtirish uchun rasmni bosing</span>}</div>
            </>
          )}
        </div>
        <form className="panel form-panel" onSubmit={(event) => void submit(event)}>
          <div><p className="eyebrow">Foydalanuvchi</p><h2>Asosiy ma’lumotlar</h2></div>
          <label className="field"><span>Foydalanuvchi ID</span><input value={userId} onChange={(event) => setUserId(event.target.value)} placeholder="Masalan: 8853120" required disabled={submitting} /></label>
          <label className="field"><span>To‘liq ism</span><input value={fullName} onChange={(event) => setFullName(event.target.value)} placeholder="Ism Familiya" required disabled={submitting} /></label>
          <div className="quality-note"><CheckCircle2 size={19} /><div><strong>Kadrda bitta yuz bo‘lsin</strong><small>{mode === 'camera' ? 'Yorug‘ joyda kameraga qarab turing.' : 'Yuz aniq va yetarlicha katta ko‘rinsin.'}</small></div></div>
          {error && <p className="error-box" role="alert">{error}</p>}
          <button className="button-primary mt-auto justify-center" disabled={submitting || (mode === 'camera' ? !ready : !image)}>{mode === 'camera' ? (busy ? `Kadr olinmoqda: ${collected} / ${TOTAL_SAMPLES}` : 'Qo‘shishni boshlash') : (upload.isPending ? 'Rasm yuklanmoqda…' : <><Upload size={17} /> Rasm orqali qo‘shish</>)}</button>
        </form>
      </div>
    </section>
  )
}
