import datetime
import math
import os
import uuid
import zipfile
from pathlib import Path

from sqlalchemy import Select
from sqlmodel import Session, select

from src.agent.state import ClassifiedClass
from src.data.dto import PagingWrapper
from src.data.model import Label
from src.dependency import PagingParams
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


def get_paging(
        params: PagingParams,
        count_statement: Select,
        execute_statement: Select,
        session: Session
):
    total_elements = int(session.exec(count_statement).one())
    total_pages = math.ceil(total_elements / params.limit)

    results = session.exec(execute_statement)
    return PagingWrapper(
        content=list(results.all()),
        first=params.offset == 0,
        last=params.offset == max(total_pages - 1, 0),
        total_elements=total_elements,
        total_pages=total_pages,
        page_number=params.offset,
        page_size=params.limit,
    )


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


# noinspection PyTypeChecker
def get_topics_from_classified_classes(classified_classes: list[ClassifiedClass]):
    from ..data.database import create_session
    with create_session() as session:
        labels = [class_name for class_name, _ in classified_classes]
        statement = (select(Label)
                     .where(Label.name in labels))
        results = session.exec(statement)
        descriptions: list[str] = [description for _, description in list(results.all())]
        topics = list(zip(classified_classes, descriptions))
    return topics
