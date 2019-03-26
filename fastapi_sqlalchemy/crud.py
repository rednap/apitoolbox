""" Generic CRUD operations """
from uuid import UUID
from typing import List, Dict, Any

from pydantic import BaseModel, PositiveInt
from starlette.exceptions import HTTPException
from starlette.concurrency import run_in_threadpool

from sqlalchemy_filters import apply_filters, apply_sort

from . import models, types

# NOTE: always use the session of the caller
# i.e. don't us models.Session in the thread pool synchronous functions
# This is necessary in sqlite3 (at least) to ensure consistency.


async def list_instances(
        cls: models.BASE,
        filter_spec: List[Dict[str, Any]] = None,
        sort_spec: List[Dict[str, str]] = None,
        offset: types.NonNegativeInt = 0,
        limit: PositiveInt = None
) -> List[dict]:
    """ Return all instances of cls """
    query = models.Session.query(cls)
    if filter_spec:
        query = apply_filters(query, filter_spec)
    if sort_spec:
        query = apply_sort(query, sort_spec)

    if limit:
        query = query.limit(limit)
    query = query.offset(offset)

    def _list():
        return [instance.as_dict() for instance in query.all()]

    return await run_in_threadpool(_list)


async def count_instances(
        cls: models.BASE,
        filter_spec: List[Dict[str, Any]] = None,
        sort_spec: List[Dict[str, Any]] = None,
) -> int:
    """ Total count of instances matching the given criteria """
    query = models.Session.query(cls)
    if filter_spec:
        query = apply_filters(query, filter_spec)
    if sort_spec:
        query = apply_sort(query, sort_spec)

    def _count():
        return query.count()

    return await run_in_threadpool(_count)


async def create_instance(cls: models.BASE, data: BaseModel) -> dict:
    """ Create an instances of cls with the provided data """
    session = models.Session()
    instance = cls(**data.dict())

    def _create():
        session.add(instance)
        session.commit()
        return session.merge(instance).as_dict()

    return await run_in_threadpool(_create)


async def retrieve_instance(cls: models.BASE, instance_id: UUID) -> dict:
    """ Get an instance of cls by UUID """
    session = models.Session()

    def _retrieve():
        instance = session.query(cls).get(instance_id)
        if instance:
            return instance.as_dict()
        return None

    data = await run_in_threadpool(_retrieve)
    if data is None:
        raise HTTPException(status_code=404)
    return data


async def update_instance(
        cls: models.BASE,
        instance_id: UUID,
        data: BaseModel) -> dict:
    """ Fully update an instances using the provided data """
    session = models.Session()

    def _update():
        instance = session.query(cls).get(instance_id)
        if not instance:
            return None
        for key, value in data.dict().items():
            setattr(instance, key, value)
        session.commit()
        return session.merge(instance).as_dict()

    data = await run_in_threadpool(_update)
    if data is None:
        raise HTTPException(status_code=404)
    return data


async def delete_instance(cls: models.BASE, instance_id: UUID) -> dict:
    """ Delete an instance by UUID """
    session = models.Session()

    def _delete():
        instance = session.query(cls).get(instance_id)
        if not instance:
            return None
        result = instance.as_dict()
        session.delete(instance)
        session.commit()
        return result

    data = await run_in_threadpool(_delete)
    if data is None:
        raise HTTPException(status_code=404)
    return data