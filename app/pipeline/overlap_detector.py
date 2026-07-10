from dataclasses import dataclass

from app.pipeline.diarization import SpeakerTurn


@dataclass(frozen=True)
class OverlapEvent:
    start_time: float
    end_time: float
    speakers: tuple[str, str]


def detect_overlaps(
    turns: list[SpeakerTurn], min_overlap_seconds: float = 0.5
) -> list[OverlapEvent]:
    events: list[OverlapEvent] = []
    ordered = sorted(turns, key=lambda turn: turn.start_time)
    for index, left in enumerate(ordered):
        for right in ordered[index + 1 :]:
            if right.start_time >= left.end_time:
                break
            overlap_start = max(left.start_time, right.start_time)
            overlap_end = min(left.end_time, right.end_time)
            if overlap_end - overlap_start >= min_overlap_seconds:
                events.append(
                    OverlapEvent(overlap_start, overlap_end, (left.speaker, right.speaker))
                )
    return events
