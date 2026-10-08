export type FaceUser = {
  id: string
  user_id: string
  full_name: string
  created_at?: string
  image_url?: string | null
}

export type FaceDetection = {
  track_id: number
  user_id?: string | null
  identity_key?: string | null
  track_count?: number
  full_name: string
  score?: number | null
  face_image?: string | null
  bbox: [number, number, number, number]
  frame_width: number
  frame_height: number
}

export type DetectionMessage = {
  faces: FaceDetection[]
  processing_ms?: number
}

export type VideoJobStatus = 'queued' | 'processing' | 'completed' | 'failed'

export type VideoJobAccepted = {
  job_id: string
  status: VideoJobStatus
}

export type VideoJobState = VideoJobAccepted & {
  progress: number
  filename: string
  error?: string | null
}

export type VideoPerson = {
  identity_key: string
  status: 'known' | 'unknown'
  user_id?: string | null
  full_name: string
  score?: number | null
  face_image?: string | null
  appearances: number
  intervals: Array<{ start: number; end: number }>
}

export type VideoAnalysisResult = {
  job_id: string
  filename: string
  duration: number
  analyzed_fps: number
  processed_frames: number
  people: VideoPerson[]
}
