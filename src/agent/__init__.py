from typing import TypedDict, Sequence, Literal

__all__ = ["agent", "StateConfiguration", "Attachment", "ClassifiedAttachment"]


class Attachment(TypedDict):
    id: str
    name: str
    mime_type: str
    save_path: str


class ClassifiedAttachment(Attachment):
    class_name: str
    probability: float


class StateConfiguration(TypedDict):
    """Configurable parameters for the agent."""
    my_configurable_param: str


class VectorStoreMetadata(TypedDict):
    name: str
    status: Literal["USE", "UNUSE"]


class AgentMetadata(TypedDict):
    status: Literal["ON", "OFF", "RESTART"]
    vector_stores: Sequence[VectorStoreMetadata] | None
