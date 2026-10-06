import type { FaceUser } from '../types'

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? '/api/v1'

async function parseResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    const body = await response.text()
    let message = body
    try {
      const parsed = JSON.parse(body) as { detail?: string }
      message = parsed.detail ?? body
    } catch {}
    throw new Error(message || `Server xatosi: ${response.status}`)
  }
  return response.json() as Promise<T>
}

export async function listFaceUsers(): Promise<FaceUser[]> {
  const response = await fetch(`${API_BASE_URL}/faces`)
  const data = await parseResponse<FaceUser[] | { items: FaceUser[] }>(response)
  return Array.isArray(data) ? data : data.items
}

export type EnrollFaceInput = {
  userId: string
  fullName: string
  image: Blob
}

export async function enrollFace(input: EnrollFaceInput): Promise<FaceUser> {
  const form = new FormData()
  form.append('user_id', input.userId)
  form.append('full_name', input.fullName)
  form.append('image', input.image, `${input.userId}.jpg`)

  const response = await fetch(`${API_BASE_URL}/faces`, {
    method: 'POST',
    body: form,
  })
  return parseResponse<FaceUser>(response)
}

export async function deleteFaceUser(userId: string): Promise<void> {
  const response = await fetch(`${API_BASE_URL}/faces/${encodeURIComponent(userId)}`, {
    method: 'DELETE',
  })
  if (!response.ok) {
    throw new Error((await response.text()) || `Server xatosi: ${response.status}`)
  }
}

export async function createWebRTCAnswer(
  offer: RTCSessionDescriptionInit,
): Promise<RTCSessionDescriptionInit> {
  const response = await fetch(`${API_BASE_URL}/webrtc/offer`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ sdp: offer.sdp, type: offer.type }),
  })
  return parseResponse<RTCSessionDescriptionInit>(response)
}

export async function createEnrollmentAnswer(
  offer: RTCSessionDescriptionInit,
  userId: string,
  fullName: string,
): Promise<RTCSessionDescriptionInit> {
  const response = await fetch(`${API_BASE_URL}/webrtc/enroll/offer`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      sdp: offer.sdp,
      type: offer.type,
      user_id: userId,
      full_name: fullName,
    }),
  })
  return parseResponse<RTCSessionDescriptionInit>(response)
}
