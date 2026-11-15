"""Durable repositories shared by API processes. Schema changes require migration."""
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import asdict

from sqlalchemy import Column, JSON, MetaData, String, Table, create_engine, delete, select, text
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert

from app.repositories.interfaces import CacheEntry
from app.schemas.analysis import JobStatusResponse
from app.schemas.results import ResultResponse
from app.schemas.receipt import ReceiptResponse
from app.schemas.spin import SpinResponse

metadata = MetaData()
records = Table('backend_records', metadata,
    Column('kind', String(32), primary_key=True),
    Column('id', String(128), primary_key=True),
    Column('result_id', String(128), index=True),
    Column('payload', JSON, nullable=False))


class Database:
    def __init__(self, url):
        options = {'pool_pre_ping': True}
        if url.startswith('sqlite'):
            options['connect_args'] = {'check_same_thread': False, 'timeout': 30}
        self.engine = create_engine(url, **options)
        self._connection = ContextVar(f'connection_{id(self)}', default=None)

    def initialize(self):
        metadata.create_all(self.engine)

    @contextmanager
    def transaction(self):
        existing = self._connection.get()
        if existing is not None:
            yield existing
            return
        with self.engine.begin() as connection:
            token = self._connection.set(connection)
            try:
                yield connection
            finally:
                self._connection.reset(token)

    def ping(self):
        with self.engine.connect() as connection:
            connection.execute(text('SELECT 1'))


class SQLRepository:
    def __init__(self, database, kind, model, id_field):
        self.database, self.kind, self.model, self.id_field = database, kind, model, id_field

    def _decode(self, payload):
        return CacheEntry(**payload) if self.model is CacheEntry else self.model.model_validate(payload)

    def add(self, item):
        payload = asdict(item) if isinstance(item, CacheEntry) else item.model_dump(mode='json')
        values = dict(kind=self.kind, id=payload[self.id_field], payload=payload,
                      result_id=payload.get('result_id'))
        dialect = self.database.engine.dialect.name
        insert = pg_insert if dialect == 'postgresql' else sqlite_insert
        statement = insert(records).values(**values)
        statement = statement.on_conflict_do_update(index_elements=['kind', 'id'],
            set_={'payload': statement.excluded.payload, 'result_id': statement.excluded.result_id})
        with self.database.transaction() as connection:
            connection.execute(statement)

    put = add
    replace = add

    def get(self, key):
        with self.database.transaction() as connection:
            payload = connection.execute(select(records.c.payload).where(
                records.c.kind == self.kind, records.c.id == key)).scalar_one_or_none()
        return self._decode(payload) if payload is not None else None

    def list_all(self):
        with self.database.transaction() as connection:
            rows = connection.execute(select(records.c.payload).where(records.c.kind == self.kind)).scalars().all()
        return [self._decode(row) for row in rows]

    def get_by_result(self, result_id):
        with self.database.transaction() as connection:
            payload = connection.execute(select(records.c.payload).where(
                records.c.kind == self.kind, records.c.result_id == result_id)).scalar_one_or_none()
        return self._decode(payload) if payload is not None else None

    def clear(self):
        with self.database.transaction() as connection:
            connection.execute(delete(records).where(records.c.kind == self.kind))


def repositories(database):
    return tuple(SQLRepository(database, *spec) for spec in (
        ('jobs', JobStatusResponse, 'job_id'), ('results', ResultResponse, 'result_id'),
        ('receipts', ReceiptResponse, 'receipt_id'), ('spins', SpinResponse, 'spin_id'),
        ('cache', CacheEntry, 'cache_key')))
