import datetime
import os
import uuid
import zipfile
from pathlib import Path
from typing import Sequence

from sqlmodel import select

from src.agent import ClassifiedAttachment
from src.data.model import Label
from src.util.constant import DEFAULT_TIMEZONE
from src.util.error import InvalidArgumentError


def convert_datetime_to_str(datetime_obj: datetime.datetime) -> str:
    """
    Convert a datetime object to string.
    `DEFAULT_TIMEZONE` is used as the timezone.
    """
    return datetime_obj.astimezone(DEFAULT_TIMEZONE).isoformat()


def convert_str_to_datetime(datetime_str: str) -> datetime.datetime:
    """
    Convert a string to a datetime object.
    The `datetime_str` must be in ISO 8601 format.
    `DEFAULT_TIMEZONE` is used as the timezone.

    Args:
        datetime_str: String representation of a datetime object

    Raises:
        ValueError: If datetime string is invalid
    """
    return datetime.datetime.fromisoformat(datetime_str).astimezone(DEFAULT_TIMEZONE)


def get_config_folder_path():
    config_path = os.getenv("AGENT_CONFIG_PATH")
    if config_path is None:
        raise RuntimeError("Missing the AGENT_CONFIG_PATH environment variable.")
    return config_path


def strict_uuid_parser(uuid_string: str) -> uuid.UUID:
    """
    Strict UUID parser that raises an exception on invalid input.

    Args:
        uuid_string: String representation of UUID

    Returns:
        uuid.UUID object

    Raises:
        InvalidArgumentError: If UUID string is invalid
    """
    try:
        return uuid.UUID(uuid_string)
    except (ValueError, TypeError) as e:
        raise InvalidArgumentError(f"Invalid UUID format: {uuid_string}") from e


def zip_folder(folder_path: str | os.PathLike[str], output_path: str | os.PathLike[str]):
    """
    Zip a folder
    :param folder_path: Path to a folder which needs to archive
    :param output_path: Path to the zip output file
    """
    folder = Path(folder_path)
    with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for file_path in folder.rglob('*'):
            if file_path.is_file():
                zipf.write(file_path, file_path.relative_to(folder))


# noinspection PyTypeChecker,PyUnresolvedReferences
def get_topics_from_classified_attachments(attachments: Sequence[ClassifiedAttachment]):
    from ..data.database import create_session
    with create_session() as session:
        labels: list[str] = [atm["class_name"] for atm in attachments]
        statement = (select(Label)
                     .where(Label.name.in_(labels)))
        results = session.exec(statement)
        descriptions: list[str] = [description for _, description in list(results.all())]
        topics = list(zip(attachments, descriptions))
    return topics
