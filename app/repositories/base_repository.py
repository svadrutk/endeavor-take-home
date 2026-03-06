from typing import TypeVar, Generic, Type, Optional, List, Any
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
import structlog

from app.database import Base

ModelType = TypeVar("ModelType", bound=Base)

logger = structlog.get_logger()


class BaseRepository(Generic[ModelType]):
    def __init__(self, db: Session, model: Type[ModelType]):
        self.db = db
        self.model = model
        self.logger = logger.bind(repository=model.__name__)

    def get(self, id: Any) -> Optional[ModelType]:
        self.logger.debug("Fetching record", id=id)
        return self.db.query(self.model).filter(self.model.id == id).first()

    def get_multi(
        self, skip: int = 0, limit: int = 100, order_by: Optional[Any] = None
    ) -> List[ModelType]:
        self.logger.debug("Fetching multiple records", skip=skip, limit=limit)
        query = self.db.query(self.model)
        if order_by is not None:
            query = query.order_by(order_by)
        return query.offset(skip).limit(limit).all()

    def create(self, obj_in: dict) -> ModelType:
        self.logger.debug("Creating record", data=obj_in)
        db_obj = self.model(**obj_in)
        self.db.add(db_obj)
        try:
            self.db.commit()
            self.db.refresh(db_obj)
            self.logger.info("Record created successfully", id=db_obj.id)
            return db_obj
        except IntegrityError as e:
            self.db.rollback()
            self.logger.error("Failed to create record", error=str(e))
            raise

    def update(self, db_obj: ModelType, obj_in: dict) -> ModelType:
        self.logger.debug("Updating record", id=db_obj.id, data=obj_in)
        for key, value in obj_in.items():
            if hasattr(db_obj, key):
                setattr(db_obj, key, value)
        self.db.commit()
        self.db.refresh(db_obj)
        self.logger.info("Record updated successfully", id=db_obj.id)
        return db_obj

    def delete(self, id: Any) -> bool:
        self.logger.debug("Deleting record", id=id)
        obj = self.db.query(self.model).filter(self.model.id == id).first()
        if obj:
            self.db.delete(obj)
            self.db.commit()
            self.logger.info("Record deleted successfully", id=id)
            return True
        self.logger.warning("Record not found for deletion", id=id)
        return False

    def count(self) -> int:
        return self.db.query(self.model).count()
