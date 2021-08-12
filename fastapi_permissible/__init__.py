from dataclasses import dataclass
from enum import Enum
from fastapi import APIRouter, HTTPException
from typing import Optional, Dict, Any, Callable
"""
permission_name as part of request??

need some way to get the users principals


input_schema == request body

output_schema == response body
"""

"""
Alternative design

Method classes for each type

"""

def inspect_resource(resource):
    methods = dict(resource._access_records)
    method_list = []
    for method, sub_methods in methods.items():
        for sub_method_name, sub_method in sub_methods.items():
            details = {
                'name': sub_method.name,
                'permissions': sub_method.permissions,
                'input_schema': sub_method.input_schema,
                'output_schema': sub_method.output_schema,
                'type_': sub_method.type_,
                'pre_process': sub_method.pre_process,
                'post_process': sub_method.post_process
            }
            method_list.append(details)
    return method_list



def try_except_dynamic(dict_of_exceptions, action, *args, **kwargs):
    try:
        return action(*args, **kwargs)
    except BaseException as e:
        if type(e) not in dict_of_exceptions:
            raise e
        else:
            raise dict_of_exceptions[type(e)]


class MethodTypes:
    post = 'post'
    #get = 'get'
    patch = 'patch'


@dataclass
class MethodConfig:
    url: str
    method_type: MethodTypes
    get_principals: Callable[..., Any]
    exceptions: Dict[Exception, HTTPException]
    status_code: int
    method_name: Optional[str] = None


def fastapi_permissible(backend, resource, **methods: MethodConfig):
    router = APIRouter()

    return router