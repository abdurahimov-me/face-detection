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
