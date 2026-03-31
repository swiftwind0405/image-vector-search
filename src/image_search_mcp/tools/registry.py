from __future__ import annotations

import inspect
import types
from dataclasses import dataclass
from typing import Callable, Literal, get_args, get_origin

from image_search_mcp.tools.context import ToolContext


@dataclass
class ToolDef:
    name: str
    description: str
    fn: Callable
    input_schema: dict


def _schema_from_hints(fn: Callable) -> dict:
    sig = inspect.signature(fn)
    params = list(sig.parameters.items())
    if params and _is_tool_context(params[0][1]):
        params = params[1:]
    properties = {}
    required = []
    for name, param in params:
        prop = _annotation_to_schema(param.annotation)
        if param.default is inspect.Parameter.empty:
            required.append(name)
        else:
            prop["default"] = param.default
        properties[name] = prop
    schema = {"type": "object", "properties": properties}
    if required:
        schema["required"] = required
    return schema


def _is_tool_context(param: inspect.Parameter) -> bool:
    try:
        return param.annotation is ToolContext or (
            isinstance(param.annotation, str) and "ToolContext" in param.annotation
        )
    except Exception:
        return False


def _annotation_to_schema(annotation) -> dict:
    origin = get_origin(annotation)
    args = get_args(annotation)
    if origin is Literal:
        return {"type": "string", "enum": list(args)}
    if origin is type(None):
        return {"type": "null"}
    if origin is types.UnionType or str(origin) == "typing.Union":
        non_none = [arg for arg in args if arg is not type(None)]
        if len(non_none) == 1:
            return _annotation_to_schema(non_none[0])
    type_map = {
        str: {"type": "string"},
        int: {"type": "integer"},
        float: {"type": "number"},
        bool: {"type": "boolean"},
    }
    if annotation in type_map:
        return type_map[annotation]
    return {}


class ToolRegistry:
    def __init__(self) -> None:
        self._tools: dict[str, ToolDef] = {}

    def tool(self, name: str, description: str):
        def decorator(fn: Callable) -> Callable:
            self._tools[name] = ToolDef(
                name=name,
                description=description,
                fn=fn,
                input_schema=_schema_from_hints(fn),
            )
            return fn

        return decorator

    def get_tools(self) -> list[ToolDef]:
        return list(self._tools.values())

    def get_tool(self, name: str) -> ToolDef | None:
        return self._tools.get(name)


registry = ToolRegistry()
