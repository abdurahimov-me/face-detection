import { Camera as CameraIcon, CameraOff, RefreshCw } from 'lucide-react'
import { forwardRef, useEffect, useImperativeHandle, useRef, useState } from 'react'

export type CameraHandle = {
  capture: () => Promise<Blob | null>
  video: HTMLVideoElement | null
}

type CameraProps = {
  children?: React.ReactNode
  onReady?: (video: HTMLVideoElement) => void
}

export const Camera = forwardRef<CameraHandle, CameraProps>(function Camera(
  { children, onReady },
  ref,
) {
  const videoRef = useRef<HTMLVideoElement>(null)
  const streamRef = useRef<MediaStream | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)

  async function openCamera() {
    setLoading(true)
    setError(null)
    streamRef.current?.getTracks().forEach((track) => track.stop())
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        video: { facingMode: 'user', width: { ideal: 1280 }, height: { ideal: 720 } },
        audio: false,
      })
      streamRef.current = stream
      if (videoRef.current) {
        videoRef.current.srcObject = stream
        await videoRef.current.play()
        onReady?.(videoRef.current)
      }
    } catch {
      setError("Kamerani ochib bo‘lmadi. Brauzer ruxsatini tekshiring.")
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    void openCamera()
    return () => streamRef.current?.getTracks().forEach((track) => track.stop())
  }, [])

  useImperativeHandle(ref, () => ({
    get video() {
      return videoRef.current
    },
    capture: () =>
      new Promise((resolve) => {
        const video = videoRef.current
        if (!video || !video.videoWidth) return resolve(null)
        const canvas = document.createElement('canvas')
        canvas.width = video.videoWidth
        canvas.height = video.videoHeight
        canvas.getContext('2d')?.drawImage(video, 0, 0)
        canvas.toBlob(resolve, 'image/jpeg', 0.9)
      }),
  }))

  return (
    <div className="camera-shell">
      <video ref={videoRef} muted playsInline className="h-full w-full object-cover" />
      <div className="camera-vignette" />
      {children}
      {loading && (
        <div className="camera-state">
          <RefreshCw className="animate-spin" size={26} />
          <span>Kamera ochilmoqda…</span>
        </div>
      )}
      {error && (
        <div className="camera-state px-6 text-center">
          <CameraOff size={32} />
          <span>{error}</span>
          <button className="button-secondary mt-2" onClick={() => void openCamera()}>
            <CameraIcon size={16} /> Qayta urinish
          </button>
        </div>
      )}
    </div>
  )
})
