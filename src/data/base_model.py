import datetime
from enum import Enum

from sqlmodel import Field, SQLModel


class BaseLabel(SQLModel):
    name: str = Field(index=True, min_length=1, max_length=255, nullable=False, unique=True)
    description: str = Field(min_length=10, nullable=False)


class BaseFile(SQLModel):
    name: str = Field(index=True, min_length=1, max_length=255, nullable=False)
    mime_type: str = Field(max_length=100, nullable=False)
    created_at: datetime.datetime = Field(nullable=False)


class BaseImage(BaseFile):
    pass


class DocumentSource(Enum):
    UPLOADED = "UPLOADED"
    EXTERNAL = "EXTERNAL"


class BaseDocument(BaseFile):
    description: str = Field(nullable=True, max_length=255)
    source: DocumentSource = Field(nullable=False)


class BaseThread(SQLModel):
    title: str = Field(min_length=1, max_length=255, nullable=False)
    created_at: datetime.datetime = Field(nullable=False)
