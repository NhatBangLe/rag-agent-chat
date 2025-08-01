from typing import Iterable
from uuid import UUID

from sqlmodel import select

from . import RepositoryImpl
from .interface.label import ILabelRepository
from ..data.model import Label, LabeledImage, Image


# noinspection PyTypeChecker
class LabelRepositoryImpl(ILabelRepository, RepositoryImpl):

    async def get_by_id(self, entity_id: UUID) -> Label | None:
        with self._connection.create_session() as session:
            entity = session.get(Label, entity_id)
            return entity

    async def get_all_by_image_id(self, image_id: UUID) -> list[Label]:
        with self._connection.create_session() as session:
            statement = (select(Label)
                         .join(LabeledImage, LabeledImage.label_id == Label.id)
                         .where(LabeledImage.image_id == image_id)
                         .order_by(LabeledImage.created_at))
            results = session.exec(statement)
            return list(results.all())

    async def get_all(self) -> list[Label]:
        with self._connection.create_session() as session:
            statement = select(Label)
            results = session.exec(statement)
            return list(results.all())

    async def get_by_name(self, name: str) -> Label | None:
        with self._connection.create_session() as session:
            stmt = select(Label).where(Label.name == name).limit(1)
            label = session.exec(stmt).one_or_none()
            return label

    # noinspection PyUnresolvedReferences
    async def get_in_names(self, names: Iterable[str]) -> list[Label] | None:
        with self._connection.create_session() as session:
            statement = (select(Label)
                         .where(Label.name.in_(names)))
            return list(session.exec(statement).all())

    # noinspection PyUnresolvedReferences
    async def assign_labels(self, image: Image, label_ids: Iterable[int]):
        with self._connection.create_session() as session:
            statement = select(Label).where(Label.id.in_(label_ids))
            matched_labels = session.exec(statement).all()
            for label in matched_labels:
                db_labeled_image = LabeledImage(label=label, image=image)
                session.add(db_labeled_image)
            session.commit()
