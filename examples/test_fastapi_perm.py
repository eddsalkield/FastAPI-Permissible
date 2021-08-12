from pydantic import BaseModel
from typing import Callable, Generator, Optional, Type
from contextlib import contextmanager

from permissible import CRUDResource, PrintCRUDBackend, \
        Create, Read, Update, Delete, Action, Permission, Principal
import asyncio
from fastapi import FastAPI, APIRouter, status
from pydantic import BaseModel
from fastapi_permissible import inspect_resource

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
#print(dict(ProfileResource._access_methods))
from pprint import pprint
pprint(inspect_resource(ProfileResource))


dict_of_exceptions = {}
app = FastAPI()
router = APIRouter()
class OutputModel(BaseModel):
    output_string: str

method = getattr(router, 'post')
@method("/admin", response_model=Profile, status_code=status.HTTP_202_ACCEPTED)
async def create_route(input_schema: Profile):
    try:
        return_model = await ProfileResource.create(
                'admin_create',
                input_schema,
                principals=[Principal('group', 'admin')],
                session=None)
    except BaseException as e:
        if type(e) not in dict_of_exceptions:
            raise e
        else:
            raise dict_of_exceptions[type(e)]
    """
    Session opened
    Creating full_name='Johnny English' age=58
    Session closed
    """

    return return_model


@router.post("/restricted", response_model=CreateProfile, status_code=status.HTTP_202_ACCEPTED)
async def create_route(input_schema: CreateProfile):
    # Invoke restricted_create to create a new profile as an unprivileged user
    return_model = await ProfileResource.create(
            'restricted_create',
            input_schema,
            principals=[Principal('group', 'user')],
            session=None)
    """
    Session opened
    Creating full_name='Mr. Bean' age=23
    Session closed
    """
    return return_model

app.include_router(router)