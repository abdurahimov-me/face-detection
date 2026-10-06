from dataclasses import dataclass


@dataclass
class TrackIdentity:
    user_id: str | None = None
    full_name: str = "Unknown"
    score: float | None = None