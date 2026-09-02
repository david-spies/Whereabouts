from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.ext.declarative import declared_attr

class Base(DeclarativeBase):
    """
    Abstract Base Model declaring automatic implicit table nomenclature generations
    and cross-entity primary data configurations.
    """
    @declared_attr
    def __tablename__(cls) -> str:
        return cls.__name__.lower()
