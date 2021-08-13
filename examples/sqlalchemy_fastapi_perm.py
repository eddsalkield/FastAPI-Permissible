from permissible.crud.backends.sqlalchemy import QuerySchema, AlreadyExistsError, NotFoundError
from typing import Callable, Generator, Optional, Type
from permissible import CRUDResource, SQLAlchemyCRUDBackend, \
        Create, Read, Update, Delete, Action, Permission, Principal

from sqlalchemy.ext.declarative import DeclarativeMeta, declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine, Text, Column, Integer
from pydantic_sqlalchemy import sqlalchemy_to_pydantic
from permissible.permissions import UnauthorisedError
from fastapi import FastAPI, status, HTTPException
from fastapi_permissible import resource_to_router, MethodConfig

DATABASE_URL = "sqlite:///./test.db"

declarative_base_instance: DeclarativeMeta = declarative_base()
engine = create_engine(
    DATABASE_URL,
    connect_args={'check_same_thread': False}
)
Session = sessionmaker(bind=engine)

class BackModel(declarative_base_instance):
    __tablename__ = 'Test_table'
    full_name = Column(Text(), primary_key = True)
    age = Column(Integer())

declarative_base_instance.metadata.create_all(engine)

ProfileBackend = SQLAlchemyCRUDBackend(BackModel, Session)

CreateProfile = sqlalchemy_to_pydantic(BackModel, exclude = ['age'])
CreateProfile.__name__ = 'CreateProfile'
Profile = ProfileBackend.Schema
DeleteProfile = ProfileBackend.DeleteSchema
OutputQuerySchema = ProfileBackend.OutputQuerySchema
# Create the profile resource
ProfileResource = CRUDResource(
        # Admin interface to create profiles
        Create[Profile, Profile](
            name='admin_create',
            permissions=[Permission(Action.ALLOW,
                                    Principal('group', 'admin'))],
            input_schema=Profile,
            output_schema=Profile
        ),
        # Restricted interface to create profiles
        Create[CreateProfile, CreateProfile](
            name='restricted_create',
            permissions=[Permission(Action.ALLOW, Principal('group', 'user'))],
            input_schema=CreateProfile,
            output_schema=CreateProfile,
            pre_process=lambda x: Profile(full_name=x.full_name, age=23),
            post_process=lambda x: CreateProfile(full_name=x.full_name)
        ),
        Read[QuerySchema, OutputQuerySchema](
            name='admin_read',
            permissions=[Permission(Action.ALLOW,
                                    Principal('group', 'admin'))],
            input_schema=QuerySchema,
            output_schema=OutputQuerySchema
        ),
        Update[Profile, Profile](
            name='admin_update',
            permissions=[Permission(Action.ALLOW,
                                    Principal('group', 'admin'))],
            input_schema=Profile,
            output_schema=Profile
        ),
        Delete[DeleteProfile, Profile](
            name='admin_delete',
            permissions=[Permission(Action.ALLOW,
                                    Principal('group', 'admin'))],
            input_schema=DeleteProfile,
            output_schema=Profile
        ),
        backend=ProfileBackend
    )

app = FastAPI()

def get_admin_principals():
    return [Principal('group', 'admin')]

def get_user_principals():
    return [Principal('group', 'user')]


exceptions = {
    UnauthorisedError: HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Unauthorised",
    ),
    AlreadyExistsError: HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="Resource already exists",
    ),
    NotFoundError: HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="Resource not found",
    )
}


router = resource_to_router(
    resource = ProfileResource, 
    admin_create = MethodConfig(
        permission_name = 'admin_create', 
        url = '/admin_create/{full_name}', 
        method_type = 'put', 
        get_principals = get_admin_principals, 
        exceptions = exceptions, 
        status_code = status.HTTP_202_ACCEPTED
    ),
    restricted_create = MethodConfig(
        permission_name = 'restricted_create', 
        url = '/restricted_create', 
        method_type = 'put', 
        get_principals = get_user_principals, 
        exceptions = exceptions, 
        status_code = status.HTTP_202_ACCEPTED
    ),
    admin_read = MethodConfig(
        permission_name = 'admin_read', 
        url = '/admin_read', 
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
    ),
    admin_update = MethodConfig(
        permission_name = 'admin_update', 
        url = '/admin_update', 
        method_type = 'patch', 
        get_principals = get_admin_principals, 
        exceptions = exceptions, 
        status_code = status.HTTP_202_ACCEPTED
    )
)
app.include_router(router)
