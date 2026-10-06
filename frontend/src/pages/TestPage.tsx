import { Activity, Radio, Wifi, WifiOff } from 'lucide-react'
import { useEffect, useRef, useState } from 'react'
import { Camera, type CameraHandle } from '../components/Camera'
import { websocketUrl } from '../lib/api'
import type { DetectionMessage } from '../types'

export function TestPage() {
  const camera = useRef<CameraHandle>(null)
  const canvas = useRef<HTMLCanvasElement>(null)
  const socket = useRef<WebSocket | null>(null)
  const awaitingResult = useRef(false)
  const [connected, setConnected] = useState(false)
  const [result, setResult] = useState<DetectionMessage>({ faces: [] })

  useEffect(() => {
    const ws = new WebSocket(websocketUrl)
    socket.current = ws
    ws.onopen = () => setConnected(true)
    ws.onclose = () => setConnected(false)
    ws.onerror = () => setConnected(false)
    ws.onmessage = (event) => {
      setResult(JSON.parse(event.data) as DetectionMessage)
      awaitingResult.current = false
    }
    return () => ws.close()
  }, [])

  useEffect(() => {
    const timer = window.setInterval(() => {
      const ws = socket.current
      const video = camera.current?.video
      if (!video || !video.videoWidth || !ws || ws.readyState !== WebSocket.OPEN || awaitingResult.current) return
      const frame = document.createElement('canvas')
      frame.width = 640
      frame.height = Math.round((video.videoHeight / video.videoWidth) * 640)
      frame.getContext('2d')?.drawImage(video, 0, 0, frame.width, frame.height)
      frame.toBlob((blob) => {
        if (!blob || ws.readyState !== WebSocket.OPEN) return
        awaitingResult.current = true
        ws.send(blob)
      }, 'image/jpeg', 0.72)
    }, 150)
    return () => window.clearInterval(timer)
  }, [])

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
      const sx = layer.width / face.frame_width
      const sy = layer.height / face.frame_height
      const [x1, y1, x2, y2] = face.bbox
      const known = Boolean(face.user_id)
      ctx.strokeStyle = known ? '#5ee9a6' : '#f8c76b'
      ctx.lineWidth = 3
      ctx.strokeRect(x1 * sx, y1 * sy, (x2 - x1) * sx, (y2 - y1) * sy)
      const label = `#${face.track_id} ${face.full_name}${face.score ? ` ${(face.score * 100).toFixed(0)}%` : ''}`
      ctx.font = '600 14px Inter, sans-serif'
      const width = ctx.measureText(label).width + 18
      const top = Math.max(0, y1 * sy - 30)
      ctx.fillStyle = known ? '#5ee9a6' : '#f8c76b'
      ctx.fillRect(x1 * sx, top, width, 28)
      ctx.fillStyle = '#07110e'
      ctx.fillText(label, x1 * sx + 9, top + 19)
    }
  }, [result])

  return (
    <section>
      <div className="page-title"><div><p className="eyebrow">Live recognition</p><h1>Kamerada test qilish</h1><p>Yangi kadr faqat oldingi natija qaytgandan keyin yuboriladi.</p></div><span className={connected ? 'connection online' : 'connection'}>{connected ? <Wifi size={16} /> : <WifiOff size={16} />}{connected ? 'Backend ulangan' : 'Backend kutilmoqda'}</span></div>
      <div className="test-grid">
        <div className="panel p-3"><Camera ref={camera}><canvas ref={canvas} className="absolute inset-0 h-full w-full" /></Camera><div className="camera-toolbar"><div><Radio className={connected ? 'text-emerald-300' : ''} size={17} /><span>{connected ? 'Jonli tanish ishlayapti' : 'WebSocket ulanmagan'}</span></div><span>{result.processing_ms ? `${result.processing_ms.toFixed(0)} ms` : '— ms'}</span></div></div>
        <aside className="panel detections-panel"><div><p className="eyebrow">Natijalar</p><h2>Kadrdagi yuzlar</h2></div>{result.faces.length === 0 ? <div className="empty-state flex-1"><Activity size={30} /><p>Yuz kutilmoqda</p></div> : <div className="detection-list">{result.faces.map((face) => <div className="detection-card" key={face.track_id}><span className={face.user_id ? 'avatar recognized' : 'avatar'}>{face.full_name.slice(0, 1)}</span><div><strong>{face.full_name}</strong><small>Track #{face.track_id}{face.user_id ? ` · ID ${face.user_id}` : ' · bazada yo‘q'}</small></div>{face.score != null && <b>{(face.score * 100).toFixed(0)}%</b>}</div>)}</div>}</aside>
      </div>
    </section>
  )
}
