import { Activity, Radio, Wifi, WifiOff } from 'lucide-react'
import { useEffect, useRef, useState } from 'react'
import { Camera, type CameraHandle } from '../components/Camera'
import { createWebRTCAnswer } from '../lib/api'
import type { DetectionMessage, FaceDetection } from '../types'

async function waitForIceGathering(peer: RTCPeerConnection): Promise<void> {
  if (peer.iceGatheringState === 'complete') return
  await new Promise<void>((resolve) => {
    const listener = () => {
      if (peer.iceGatheringState === 'complete') {
        peer.removeEventListener('icegatheringstatechange', listener)
        resolve()
      }
    }
    peer.addEventListener('icegatheringstatechange', listener)
  })
}

export function TestPage() {
  const camera = useRef<CameraHandle>(null)
  const canvas = useRef<HTMLCanvasElement>(null)
  const peer = useRef<RTCPeerConnection | null>(null)
  const [connected, setConnected] = useState(false)
  const [connectionError, setConnectionError] = useState<string | null>(null)
  const [result, setResult] = useState<DetectionMessage>({ faces: [] })
  const [detectedFaces, setDetectedFaces] = useState<FaceDetection[]>([])

  async function startWebRTC(video: HTMLVideoElement) {
    peer.current?.close()
    setConnected(false)
    setConnectionError(null)
    setDetectedFaces([])
    const connection = new RTCPeerConnection()
    peer.current = connection
    const dataChannel = connection.createDataChannel('detections')
    dataChannel.onopen = () => setConnected(true)
    dataChannel.onclose = () => setConnected(false)
    dataChannel.onmessage = (event) => {
      const message = JSON.parse(event.data) as DetectionMessage
      setResult(message)
      setDetectedFaces((previous) => {
        let next = [...previous]
        for (const face of message.faces) {
          if (!face.identity_key) continue
          const existing = next.find(
            (item) =>
              item.identity_key === face.identity_key || item.track_id === face.track_id,
          )
          const merged = {
            ...existing,
            ...face,
            face_image: face.face_image ?? existing?.face_image,
          }
          next = [
            merged,
            ...next.filter(
              (item) =>
                item.track_id !== face.track_id &&
                item.identity_key !== face.identity_key,
            ),
          ]
        }
        return next.slice(0, 20)
      })
    }
    connection.onconnectionstatechange = () => {
      setConnected(connection.connectionState === 'connected')
      if (connection.connectionState === 'failed') {
        setConnectionError('Kamera bilan aloqa o‘rnatilmadi.')
      }
    }

    const stream = video.srcObject as MediaStream | null
    stream?.getVideoTracks().forEach((track) => connection.addTrack(track, stream))
    try {
      await connection.setLocalDescription(await connection.createOffer())
      await waitForIceGathering(connection)
      const answer = await createWebRTCAnswer(connection.localDescription!)
      await connection.setRemoteDescription(answer)
    } catch (error) {
      connection.close()
      setConnectionError(error instanceof Error ? error.message : 'Ulanishda xatolik yuz berdi.')
    }
  }

  useEffect(() => () => peer.current?.close(), [])

  useEffect(() => {
    const layer = canvas.current
    const video = camera.current?.video
    if (!layer || !video) return
    const rect = video.getBoundingClientRect()
    layer.width = rect.width
    layer.height = rect.height
    const ctx = layer.getContext('2d')
    if (!ctx) return
    ctx.clearRect(0, 0, layer.width, layer.height)
    for (const face of result.faces) {
      const scale = Math.max(
        layer.width / face.frame_width,
        layer.height / face.frame_height,
      )
      const offsetX = (layer.width - face.frame_width * scale) / 2
      const offsetY = (layer.height - face.frame_height * scale) / 2
      const [x1, y1, x2, y2] = face.bbox
      const left = layer.width - (offsetX + x2 * scale)
      const top = offsetY + y1 * scale
      const width = (x2 - x1) * scale
      const height = (y2 - y1) * scale
      const known = Boolean(face.user_id)
      ctx.strokeStyle = known ? '#5ee9a6' : '#f8c76b'
      ctx.lineWidth = 3
      ctx.strokeRect(left, top, width, height)
      const label = `#${face.track_id} ${face.full_name}${face.score != null ? ` ${(face.score * 100).toFixed(0)}%` : ''}`
      ctx.font = '600 14px Inter, sans-serif'
      const labelWidth = ctx.measureText(label).width + 18
      const labelTop = Math.max(0, top - 30)
      ctx.fillStyle = known ? '#5ee9a6' : '#f8c76b'
      ctx.fillRect(left, labelTop, labelWidth, 28)
      ctx.fillStyle = '#07110e'
      ctx.fillText(label, left + 9, labelTop + 19)
    }
  }, [result])

  return (
    <section>
      <div className="page-title"><div><p className="eyebrow">Kamera orqali</p><h1>Yuzni tekshirish</h1><p>Kamera oldidagi odamlar ro‘yxatdagi foydalanuvchilar bilan solishtiriladi.</p></div><span className={connected ? 'connection online' : 'connection'}>{connected ? <Wifi size={16} /> : <WifiOff size={16} />}{connected ? 'Kamera tayyor' : 'Ulanmoqda'}</span></div>
      <div className="test-grid">
        <div className="panel p-3"><Camera ref={camera} onReady={(video) => void startWebRTC(video)}><canvas ref={canvas} className="absolute inset-0 h-full w-full" /></Camera><div className="camera-toolbar"><div><Radio className={connected ? 'text-emerald-300' : ''} size={17} /><span>{connectionError ?? (connected ? 'Yuzni aniqlash ishlayapti' : 'Kamera tayyorlanmoqda…')}</span></div><span>{connected ? 'Jonli' : '—'}</span></div></div>
        <aside className="panel detections-panel"><div><p className="eyebrow">Natijalar</p><h2>Topilgan odamlar</h2></div>{detectedFaces.length === 0 ? <div className="empty-state flex-1"><Activity size={30} /><p>Yuz kutilmoqda</p></div> : <div className="detection-list">{detectedFaces.map((face) => <div className="detection-card" key={face.identity_key}><span className={`${face.user_id ? 'avatar recognized' : 'avatar'} detection-face`}>{face.face_image ? <img src={face.face_image} alt={face.full_name} /> : face.full_name.slice(0, 1)}</span><div><strong>{face.full_name}</strong><small>{face.user_id ? `ID ${face.user_id}` : 'Ro‘yxatda yo‘q'} · {face.track_count ?? 1} marta ko‘rindi</small></div></div>)}</div>}</aside>
      </div>
    </section>
  )
}
