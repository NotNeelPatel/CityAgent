from typing import TypedDict, Literal, NotRequired

EventType = Literal["loading", "chunking", "embedding", "success", "error"]


class VectorizeEvent(TypedDict):
    type: EventType
    message: NotRequired[str]
    file_path: NotRequired[str]
    chunks_created: NotRequired[int]
    chunks_to_create: NotRequired[int]
    chunks_embedded: NotRequired[int]
    total_chunks: NotRequired[int]
    detail: NotRequired[str]


def make_event(event_type: EventType, **kwargs) -> VectorizeEvent:
    return {"type": event_type, **kwargs}
