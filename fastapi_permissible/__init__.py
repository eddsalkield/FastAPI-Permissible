from dataclasses import dataclass
from enum import Enum
from fastapi import APIRouter, HTTPException
from typing import Optional, Dict, Any, Callable
import re
"""
permission_name as part of request??

need some way to get the users principals


input_schema == request body

output_schema == response body
"""

"""
Alternative design

Method classes for each type

items specified in the url that feature in the input schema get put into the positional parameters
else fail



"""

def inspect_resource(resource):
    methods = dict(resource._access_records)
    method_dict = {}
    for method, sub_methods in methods.items():
        for sub_method_name, sub_method in sub_methods.items():
            details = {
                'permissions': sub_method.permissions,
                'input_schema': sub_method.input_schema,
                'output_schema': sub_method.output_schema,
                'type_': sub_method.type_,
                'pre_process': sub_method.pre_process,
                'post_process': sub_method.post_process
            }
            method_dict[sub_method.name] = details
    return method_dict

def get_url_positionals(url):
    return [i[1:-1] for i in re.findall('{\w+}', url)]


class MethodTypes(Enum):
    post = 'post'
    get = 'get'
    head = 'head',
    put = 'put'
    delete = 'delete'
    connect = 'connect'
    options = 'options'
    trace = 'trace'
    patch = 'patch'

@dataclass
class MethodConfig:
    permission_name: str
    url: str
    method_type: MethodTypes
    get_principals: Callable[..., Any]
    exceptions: Dict[Exception, HTTPException]
    status_code: int

def rename_func(newname):
    def decorator(f):
        f.__name__ = newname
        return f
    return decorator

def resource_to_router(resource, **methods: MethodConfig):
    router = APIRouter()
    resource_details = inspect_resource(resource)
    for method_name, method_config in methods.items():
        relevent_details = resource_details[method_config.permission_name]
        input_schema = relevent_details['input_schema']
        output_schema = relevent_details['output_schema']
        router_method = getattr(router, method_config.method_type)
        resource_method = getattr(resource, relevent_details['type_'].value)
        def make_route_function(input_schema, method_config):
            async def route_name(input_data: input_schema):
                try:
                    return_model = await resource_method(
                        method_config.permission_name,
                        input_data,
                        principals = method_config.get_principals(),
                        session = None
                    )
                    return return_model
                except BaseException as e:
                    if type(e) not in method_config.exceptions:
                        raise e
                    else:
                        raise method_config.exceptions[type(e)]
            return route_name
        route_func = make_route_function(input_schema, method_config)
        rename_func(method_name)(route_func)
        router_method(method_config.url, response_model = output_schema, status_code = method_config.status_code)(route_func)

    return router