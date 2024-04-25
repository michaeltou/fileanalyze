# coding: utf-8
from sqlalchemy import Column, String, Text, DateTime, Integer
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime

Base = declarative_base()
metadata = Base.metadata


def create_tables(engine):
    metadata.create_all(engine)


class MceCalcObjectInfo(Base):
    __tablename__ = 'mce_calc_object_info'

    object_id = Column(String(50), primary_key=True)
    object_name = Column(String(50))
    custom_tag = Column(String(50))
    parent_id = Column(String(50))
    python_code = Column(Text)
    python_expr = Column(String(200))
    lru_maxsize = Column(Integer, default=0)
    ttl_seconds = Column(Integer, default=0)
    remark = Column(String(200))
    sort_number = Column(Integer, default=0)
    last_updated_time = Column(DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {k: getattr(self, k, None) for k in self.__table__.c.keys()}
