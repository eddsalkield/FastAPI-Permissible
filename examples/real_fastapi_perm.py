from pydantic import BaseModel
from typing import Callable, Generator, Optional, Type
from contextlib import contextmanager

from permissible import CRUDResource, PrintCRUDBackend, \
        Create, Read, Update, Delete, Action, Permission, Principal
from permissible.permissions import UnauthorisedError
import asyncio
from fastapi import FastAPI, APIRouter, status, HTTPException
from pydantic import BaseModel
from fastapi_permissible import inspect_resource, resource_to_router, MethodConfig

class Profile(BaseModel):
    """
    The base model, defining the complete attributes of a profile.
    """
    full_name: str
    age: int


class CreateProfile(BaseModel):
    """
    The restricted interface for creating profiles.
    Does not permit the user to select an age.
    """
    full_name: str


# Create the profile backend
ProfileBackend = PrintCRUDBackend(
    Profile, Profile, Profile, Profile
)

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
    backend=ProfileBackend
)

app = FastAPI()

def get_admin_principals():
    return [Principal('group', 'admin')]

def get_user_principals():
    return [Principal('group', 'user')]


exceptions = {
    ValueError: HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="ValueError",
    ),
    UnauthorisedError: HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Unauthorised",
    )
}


router = resource_to_router(
    resource = ProfileResource, 
    admin_create = MethodConfig(
        permission_name = 'admin_create', 
        url = '/admin_create/{full_name}', 
        method_type = 'post', 
        get_principals = get_admin_principals, 
        exceptions = exceptions, 
        status_code = status.HTTP_202_ACCEPTED
    ),
    restricted_create = MethodConfig(
        permission_name = 'restricted_create', 
        url = '/restricted_create', 
        method_type = 'post', 
        get_principals = get_user_principals, 
        exceptions = exceptions, 
        status_code = status.HTTP_202_ACCEPTED
    )
)
app.include_router(router)