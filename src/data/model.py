import datetime
from uuid import UUID, uuid4

from sqlmodel import Field, SQLModel, Relationship

from .base_model import BaseImage, BaseLabel, BaseDocument, BaseThread


class User(SQLModel, table=True):
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    uploaded_images: list["Image"] = Relationship(back_populates="user")
    created_threads: list["Thread"] = Relationship(back_populates="user")


class Label(BaseLabel, table=True):
    id: int | None = Field(ge=0, default=None, primary_key=True)
    labeled_images: list["LabeledImage"] = Relationship(back_populates="label")


class Image(BaseImage, table=True):
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    save_path: str = Field(nullable=False)
    has_labels: list["LabeledImage"] = Relationship(back_populates="image")
    user_id: UUID = Field(description="Who uploaded this image", foreign_key="user.id", nullable=False)
    user: User = Relationship(back_populates="uploaded_images")


class LabeledImage(SQLModel, table=True):
    label_id: int = Field(foreign_key="label.id", primary_key=True)
    image_id: UUID = Field(foreign_key="image.id", primary_key=True)
    created_at: datetime.datetime = Field(nullable=False)

    label: Label = Relationship(back_populates="labeled_images")
    image: Image = Relationship(back_populates="has_labels")


class Document(BaseDocument, table=True):
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    embed_to_vs: str | None = Field(description="Name of the vector store that document is embedded to",
                                    default=None, nullable=True, max_length=100)
    embed_bm25: bool = Field(description="Whether this document is embedded to BM25 index", default=False)
    save_path: str | None = Field(nullable=True)
    chunks: list["DocumentChunk"] = Relationship(back_populates="document")


class DocumentChunk(SQLModel, table=True):
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    document_id: UUID = Field(foreign_key="document.id", nullable=False)
    document: Document = Relationship(back_populates="chunks")


class Thread(BaseThread, table=True):
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    user_id: UUID = Field(foreign_key="user.id", nullable=False)
    user: User = Relationship(back_populates="created_threads")
