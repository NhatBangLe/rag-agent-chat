from uuid import UUID

from pydantic import BaseModel, Field

from .base_model import BaseImage, BaseLabel, BaseDocument, BaseThread


class LabelPublic(BaseLabel):
    id: int


class LabelCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=255)


class LabelUpdate(BaseModel):
    description: str | None = Field(default=None, max_length=255)


class LabelDelete(BaseModel):
    id: int | None = Field(default=None, ge=1)
    name: str | None = Field(default=None, min_length=1)


class ImageCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    mime_type: str | None = Field(default=None, max_length=150)
    data: bytes = Field(min_length=1)


class ImagePublic(BaseImage):
    id: UUID
    name: str | None = Field(default=None, min_length=1)
    mime_type: str | None = Field(default=None)
    assigned_label_ids: list[int] | None = Field(default=None)
    classified_label_ids: list[int] | None = Field(default=None)


class DocumentCreate(BaseModel):
    name: str = Field(min_length=1, max_length=150)
    description: str | None = Field(default=None, max_length=255)
    mime_type: str | None = Field(default=None, max_length=150)
    data: bytes = Field(min_length=1)


class DocumentPublic(BaseDocument):
    id: UUID
    mime_type: str | None = Field(default=None, min_length=1)
    embedded_to_vs: str | None = Field(default=None, min_length=1)
    embedded_to_bm25: bool = Field(default=False)


class AttachmentPublic(BaseModel):
    id: str = Field(description="Unique identifier of the attachment.", min_length=1)
    name: str = Field(description="Name of the attachment.", min_length=1)
    mime_type: str = Field(description="MIME type of the attachment.", min_length=1)
    url: str = Field(description="Path to the attachment.")


class InputMessage(BaseModel):
    attachment_id: str | None = Field(default=None)
    content: str = Field(default="")


class ThreadPublic(BaseThread):
    id: UUID


class ThreadCreate(BaseModel):
    title: str = Field(min_length=1, max_length=255)


class ThreadUpdate(BaseModel):
    title: str = Field(min_length=1, max_length=255)
