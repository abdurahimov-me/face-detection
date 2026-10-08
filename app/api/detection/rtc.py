import asyncio
import typing as t

from aiortc import RTCSessionDescription, RTCPeerConnection

from resources.detection.data import peer_connections
from resources.detection.sessions.recognation import RecognitionSession
from .services import ensure_faces_collection, resolve_identity


async def create_webrtc_answer(sdp: str, description_type: str) -> RTCSessionDescription:
    await ensure_faces_collection()
    peer = RTCPeerConnection()
    peer_connections.add(peer)
    session = RecognitionSession(resolve_identity)
    channel_holder: t.Dict = {}
    video_tasks: t.Set[asyncio.Task] = set()

    @peer.on('datachannel')
    def on_datachannel(channel) -> None:
        if channel.label == 'detections':
            channel_holder['channel'] = channel

    @peer.on('track')
    def on_track(track) -> None:
        if track.kind == 'video':
            task = asyncio.create_task(session.consume_video(track, channel_holder))
            video_tasks.add(task)
            task.add_done_callback(video_tasks.discard)

    @peer.on('connectionstatechange')
    async def on_connectionstatechange() -> None:
        if peer.connectionState in {'failed', 'closed', 'disconnected'}:
            for task in video_tasks:
                task.cancel()
            await peer.close()
            peer_connections.remove(peer)

    try:
        await peer.setRemoteDescription(
            RTCSessionDescription(sdp=sdp, type=description_type)
        )
        answer = await peer.createAnswer()
        await peer.setLocalDescription(answer)
        return peer.localDescription
    except Exception:
        await peer.close()
        peer_connections.remove(peer)
        raise
