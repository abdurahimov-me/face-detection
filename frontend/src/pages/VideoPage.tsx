import { useMutation, useQuery } from '@tanstack/react-query'
import {
  CheckCircle2,
  Clock3,
  Film,
  LoaderCircle,
  UploadCloud,
  UserCheck,
  UserRoundX,
  Users,
  X,
} from 'lucide-react'
import { useEffect, useMemo, useRef, useState } from 'react'
import {
  createVideoAnalysis,
  getVideoAnalysis,
  getVideoAnalysisResult,
} from '../lib/api'

function formatTime(seconds: number) {
  const minutes = Math.floor(seconds / 60)
  const rest = Math.floor(seconds % 60)
  return `${minutes}:${rest.toString().padStart(2, '0')}`
}

export function VideoPage() {
  const input = useRef<HTMLInputElement>(null)
  const [file, setFile] = useState<File | null>(null)
  const [previewUrl, setPreviewUrl] = useState<string | null>(null)
  const [jobId, setJobId] = useState<string | null>(null)

  useEffect(() => {
    if (!file) {
      setPreviewUrl(null)
      return
    }
    const url = URL.createObjectURL(file)
    setPreviewUrl(url)
    return () => URL.revokeObjectURL(url)
  }, [file])

  const upload = useMutation({
    mutationFn: createVideoAnalysis,
    onSuccess: (job) => setJobId(job.job_id),
  })
  const status = useQuery({
    queryKey: ['video-analysis', jobId],
    queryFn: () => getVideoAnalysis(jobId!),
    enabled: Boolean(jobId),
    refetchInterval: (query) => {
      const value = query.state.data?.status
      return value === 'completed' || value === 'failed' ? false : 800
    },
  })
  const result = useQuery({
    queryKey: ['video-analysis-result', jobId],
    queryFn: () => getVideoAnalysisResult(jobId!),
    enabled: Boolean(jobId) && status.data?.status === 'completed',
    staleTime: Infinity,
    retry: false,
  })

  const summary = useMemo(() => {
    const people = result.data?.people ?? []
    return {
      known: people.filter((person) => person.status === 'known').length,
      unknown: people.filter((person) => person.status === 'unknown').length,
    }
  }, [result.data])

  const busy = upload.isPending || status.data?.status === 'queued' || status.data?.status === 'processing'
  const error = upload.error ?? status.error ?? result.error

  function selectFile(next: File | undefined) {
    if (!next || busy) return
    setFile(next)
    setJobId(null)
    upload.reset()
  }

  function reset() {
    setFile(null)
    setJobId(null)
    upload.reset()
  }

  return (
    <section>
      <div className="page-title video-page-title">
        <div>
          <p className="eyebrow">Video tahlili</p>
          <h1>Videodagi odamlarni toping</h1>
          <p>Video bir martalik tahlil qilinadi. Fayl va vaqtinchalik ma’lumotlar jarayon tugashi bilan o‘chiriladi.</p>
        </div>
        {status.data && (
          <span className={`job-state ${status.data.status}`}>
            {status.data.status === 'completed' ? <CheckCircle2 size={16} /> : <LoaderCircle size={16} />}
            {status.data.status === 'queued' && 'Navbatda'}
            {status.data.status === 'processing' && 'Tahlil qilinmoqda'}
            {status.data.status === 'completed' && 'Tayyor'}
            {status.data.status === 'failed' && 'Xatolik'}
          </span>
        )}
      </div>

      {!result.data && (
        <div className="video-workspace">
          <div
            className={`video-dropzone ${file ? 'has-file' : ''}`}
            onDragOver={(event) => event.preventDefault()}
            onDrop={(event) => {
              event.preventDefault()
              selectFile(event.dataTransfer.files[0])
            }}
          >
            {previewUrl ? (
              <video src={previewUrl} controls preload="metadata" />
            ) : (
              <button type="button" className="dropzone-empty" onClick={() => input.current?.click()}>
                <span><UploadCloud size={28} /></span>
                <strong>Videoni shu yerga tashlang</strong>
                <small>yoki kompyuterdan tanlang · MP4, MOV, AVI, WebM · 500 MB gacha</small>
              </button>
            )}
            <input
              ref={input}
              hidden
              type="file"
              accept="video/mp4,video/quicktime,video/x-msvideo,video/webm,video/x-matroska"
              onChange={(event) => selectFile(event.target.files?.[0])}
            />
          </div>

          <aside className="panel video-side-panel">
            <div>
              <p className="eyebrow">Bir martalik</p>
              <h2>{file ? file.name : 'Video tanlanmagan'}</h2>
              <p>{file ? `${(file.size / 1024 / 1024).toFixed(1)} MB` : 'Tahlil boshlanishi uchun video fayl tanlang.'}</p>
            </div>

            {busy && (
              <div className="analysis-progress">
                <div><span>Tahlil jarayoni</span><b>{Math.round(status.data?.progress ?? 0)}%</b></div>
                <div className="progress-track"><span style={{ width: `${status.data?.progress ?? 0}%` }} /></div>
                <small><Clock3 size={14} /> Video uzunligiga qarab biroz vaqt olishi mumkin.</small>
              </div>
            )}

            {(error || status.data?.error) && (
              <div className="error-box">{status.data?.error ?? (error instanceof Error ? error.message : 'Xatolik yuz berdi.')}</div>
            )}

            <div className="video-actions">
              {file && !busy && !jobId && (
                <button className="button-primary" onClick={() => upload.mutate(file)}>
                  <Film size={17} /> Tahlilni boshlash
                </button>
              )}
              {file && !busy && (
                <button className="button-secondary" onClick={reset}><X size={17} /> Tozalash</button>
              )}
            </div>
          </aside>
        </div>
      )}

      {result.data && (
        <div className="video-results">
          <div className="result-summary">
            <div><span><Users size={20} /></span><small>Jami odam</small><strong>{result.data.people.length}</strong></div>
            <div><span><UserCheck size={20} /></span><small>Ro‘yxatda bor</small><strong>{summary.known}</strong></div>
            <div><span><UserRoundX size={20} /></span><small>Noma’lum</small><strong>{summary.unknown}</strong></div>
            <div><span><Clock3 size={20} /></span><small>Video</small><strong>{formatTime(result.data.duration)}</strong></div>
          </div>

          <div className="panel result-panel">
            <div className="panel-heading">
              <div><p className="eyebrow">Natija</p><h2>Videoda topilgan noyob odamlar</h2></div>
              <button className="button-secondary" onClick={reset}>Yangi video</button>
            </div>
            {result.data.people.length === 0 ? (
              <div className="empty-state"><Users size={30} /><p>Videoda yuz topilmadi</p></div>
            ) : (
              <div className="video-people-grid">
                {result.data.people.map((person) => (
                  <article className="video-person-card" key={person.identity_key}>
                    <div className="video-person-image">
                      {person.face_image ? <img src={person.face_image} alt={person.full_name} /> : <Users size={28} />}
                      <span className={person.status}>{person.status === 'known' ? 'Ro‘yxatda bor' : 'Noma’lum'}</span>
                    </div>
                    <div className="video-person-copy">
                      <h3>{person.full_name}</h3>
                      <p>{person.user_id ? `ID ${person.user_id}` : 'Ro‘yxatda yo‘q'}</p>
                      <div className="person-meta">
                        <span>{person.appearances} marta ko‘rindi</span>
                        {person.score != null && <span>{Math.round(person.score * 100)}%</span>}
                      </div>
                      <div className="time-chips">
                        {person.intervals.map((interval, index) => (
                          <span key={`${interval.start}-${index}`}>{formatTime(interval.start)}–{formatTime(interval.end)}</span>
                        ))}
                      </div>
                    </div>
                  </article>
                ))}
              </div>
            )}
          </div>
        </div>
      )}
    </section>
  )
}
