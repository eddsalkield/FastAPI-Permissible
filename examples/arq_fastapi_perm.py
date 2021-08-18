from arq import create_pool
from permissible.crud.backends.arq import ARQBackend, CreateSchema, ARQSessionMaker, GetSchema, ArqSessionAbortFailure, JobPromiseModel, JobModel, GetModel, PoolJobCompleted, PoolJobNotFound, UpdateSchema
import asyncio
from permissible import CRUDResource, Create, Read, Update, Delete, Permission, Action, Principal
from arq.connections import RedisSettings
import time
from random import random
from math import log10
from pydantic import BaseModel
from typing import Optional, Any
from datetime import datetime
from fastapi import FastAPI, status, HTTPException
from fastapi_permissible import resource_to_router, MethodConfig
from permissible.permissions import UnauthorisedError
async def test_func(ctx):
    random_3 = 2*random()
    for i in range(20000000):
        list_of_list = log10(abs(log10(random_3**random_3**random_3)))
    return list_of_list
data = {}

app = FastAPI()

def get_admin_principals():
    return [Principal('group', 'admin')]

exceptions = {
    UnauthorisedError: HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Unauthorised",
    ),
    PoolJobNotFound: HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="Pool job not found"
    ),
    PoolJobCompleted: HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="Pool job already completed"
    )
}

@app.on_event("startup")
async def app_startup():
    data['pool'] = await create_pool()
    data['session_maker'] = ARQSessionMaker(pool=data['pool'])

    sessionmaker = data['session_maker']
    backend = ARQBackend(sessionmaker)
    ProfileResource = CRUDResource(
        # Admin interface to create profiles
        Create[CreateSchema, JobPromiseModel](
            name='admin_create',
            permissions=[Permission(Action.ALLOW, Principal('group', 'admin'))],
            input_schema=CreateSchema,
            output_schema=GetModel
        ),
        Read[GetSchema, GetModel](
            name='admin_read',
            permissions=[Permission(Action.ALLOW, Principal('group', 'admin'))],
            input_schema=GetSchema,
            output_schema=GetModel
        ),
        Delete[GetSchema, GetModel](
            name='admin_delete',
            permissions=[Permission(Action.ALLOW, Principal('group', 'admin'))],
            input_schema=GetSchema,
            output_schema=GetModel
        ),
        backend=backend
    )

    router = resource_to_router(
        ProfileResource,
        admin_create = MethodConfig(
            permission_name = 'admin_create', 
            url = '/admin_create/{function}', 
            method_type = 'put', 
            get_principals = get_admin_principals, 
            exceptions = exceptions, 
            status_code = status.HTTP_202_ACCEPTED
        ),
        admin_read = MethodConfig(
            permission_name = 'admin_read',
            url = '/admin_read/{job_id}', 
            method_type = 'post', 
            get_principals = get_admin_principals, 
            exceptions = exceptions, 
            status_code = status.HTTP_202_ACCEPTED
        ),
        admin_delete = MethodConfig(
            permission_name = 'admin_delete',
            url = '/admin_delete',
            method_type = 'delete',
            get_principals = get_admin_principals,
            exceptions = exceptions,
            status_code = status.HTTP_202_ACCEPTED
        )
    )
    app.include_router(router)


class WorkerSettings:
    functions = [test_func]
    allow_abort_jobs = True

