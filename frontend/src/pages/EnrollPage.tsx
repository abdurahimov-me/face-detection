import { useNavigate } from '@tanstack/react-router'
import { useQueryClient } from '@tanstack/react-query'
import { CheckCircle2, ScanFace } from 'lucide-react'
import { FormEvent, useEffect, useRef, useState } from 'react'
import { Camera, type CameraHandle } from '../components/Camera'
import { createEnrollmentAnswer } from '../lib/api'
import { faceUsersQueryKey } from '../lib/queries'

const TOTAL_SAMPLES = 3

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
  const navigate = useNavigate()
  const [userId, setUserId] = useState('')
  const [fullName, setFullName] = useState('')
  const [ready, setReady] = useState(false)
  const [busy, setBusy] = useState(false)
  const [collected, setCollected] = useState(0)
  const [message, setMessage] = useState('Kameraga qarang va boshlash tugmasini bosing.')
  const [error, setError] = useState<string | null>(null)

  useEffect(() => () => peer.current?.close(), [])

  async function submit(event: FormEvent) {
    event.preventDefault()
    const video = camera.current?.video
    const stream = video?.srcObject as MediaStream | null
    const track = stream?.getVideoTracks()[0]
    if (!track || busy) return

    peer.current?.close()
    const connection = new RTCPeerConnection()
    peer.current = connection
    setBusy(true)
    setCollected(0)
    setError(null)
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
      <div className="page-title"><div><p className="eyebrow">Yangi foydalanuvchi</p><h1>Foydalanuvchi qo‘shish</h1><p>Kameraga qarang. Eng yaxshi kadrlar avtomatik tanlanadi.</p></div></div>
      <div className="work-grid">
        <div className="panel p-3">
          <Camera ref={camera} onReady={() => setReady(true)}><div className="face-guide"><span /><span /><span /><span /></div></Camera>
          <div className="camera-toolbar"><div><ScanFace size={17} /><span>{message}</span></div><span>{collected} / {TOTAL_SAMPLES}</span></div>
        </div>
        <form className="panel form-panel" onSubmit={(event) => void submit(event)}>
          <div><p className="eyebrow">Foydalanuvchi</p><h2>Asosiy ma’lumotlar</h2></div>
          <label className="field"><span>Foydalanuvchi ID</span><input value={userId} onChange={(event) => setUserId(event.target.value)} placeholder="Masalan: 8853120" required disabled={busy} /></label>
          <label className="field"><span>To‘liq ism</span><input value={fullName} onChange={(event) => setFullName(event.target.value)} placeholder="Ism Familiya" required disabled={busy} /></label>
          <div className="quality-note"><CheckCircle2 size={19} /><div><strong>Kadrda bitta yuz bo‘lsin</strong><small>Yorug‘ joyda kameraga qarab turing.</small></div></div>
          {error && <p className="error-box">{error}</p>}
          <button className="button-primary mt-auto justify-center" disabled={!ready || busy}>{busy ? `Kadr olinmoqda: ${collected} / ${TOTAL_SAMPLES}` : 'Qo‘shishni boshlash'}</button>
        </form>
      </div>
    </section>
  )
}
