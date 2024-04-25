from sqlalchemy import MetaData
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.automap import automap_base
from datetime import datetime
from contextlib import contextmanager


class DBOperator:
    def __init__(self, engine, entity):
        self.__engine = engine
        self.__entity = entity

    @property
    def engine(self):
        return self.__engine

    @property
    def entity(self):
        return self.__entity

    @contextmanager
    def create_session(self):
        session = sessionmaker(bind=self.__engine)()
        try:
            yield session
        finally:
            session.close()

    def add(self, **kwargs):
        with self.create_session() as session:
            session.add(self.__entity(**kwargs))
            session.commit()

    def delete(self, *criterion):
        with self.create_session() as session:
            ret = session.query(self.__entity).filter(*criterion).delete()
            session.commit()
            return ret

    def update(self, *criterion, **kwargs):
        if hasattr(self.entity, 'last_updated_time'):
            kwargs['last_updated_time'] = datetime.utcnow()

        with self.create_session() as session:
            ret = session.query(self.__entity).filter(*criterion).update(kwargs)
            session.commit()
            return ret

    def query(self, *criterion, header=None):
        with self.create_session() as session:
            if header is None:
                return session.query(self.__entity).filter(*criterion).all()
            else:
                return session.query(self.__entity).filter(*criterion).limit(header).all()

    def custom_query(self, func):
        with self.create_session() as session:
            if callable(func):
                return func(session)


class DynamicOperator(DBOperator):
    def __init__(self, engine, table_name):
        self.__table_name = table_name.lower()
        metadata = MetaData()
        metadata.reflect(engine, only=[self.__table_name])
        base = automap_base(metadata=metadata)
        base.prepare()
        super(DynamicOperator, self).__init__(engine, entity=base.classes[self.__table_name])

    @property
    def table_name(self):
        return self.__table_name
