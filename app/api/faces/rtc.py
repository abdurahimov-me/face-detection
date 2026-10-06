import asyncio

from aiortc import RTCSessionDescription, RTCPeerConnection

from resources.detection.data import peer_connections
from .services import EnrollmentSession, check_user_id_available, validate_user_fields


async def create_enrollment_answer(
        sdp: str, description_type: str, user_id: str, full_name: str
) -> RTCSessionDescription:
    user_id, full_name = validate_user_fields(user_id, full_name)
    await check_user_id_available(user_id)
    peer = RTCPeerConnection()
    peer_connections.add(peer)
    session = EnrollmentSession(user_id, full_name)
    channel_holder: dict = {}
    video_tasks: set[asyncio.Task] = set()

    @peer.on('datachannel')
    def on_datachannel(channel) -> None:
        if channel.label == 'enrollment':
            channel_holder['channel'] = channel

    @peer.on('track')
    def on_track(track) -> None:
        if track.kind == 'video':
            task = asyncio.create_task(session.consume(track, channel_holder))
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
