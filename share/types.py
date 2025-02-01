"""
@description: this file contains all types this project uses
"""

from __future__ import annotations
from dataclasses import dataclass, asdict
from typing import (
    Dict as _Dict,
    List as _List,
    Tuple as _Tuple,
    Optional as _Optional,
    Type as _Type,
    Callable as _Callable,
    Any as _Any,
    Iterable as _Iterable,
    Literal as _Literal,
    TypeVar as _TypeVar,
    Generator as _Generator,
    TYPE_CHECKING as _TYPE_CHECKING,
)

from dacite import from_dict, Config as dacite_config


Type = _Type
Dict = _Dict
List = _List
Tuple = _Tuple
Optional = _Optional
Callable = _Callable
Any = _Any
Iterable = _Iterable
Literal = _Literal
TypeVar = _TypeVar
Generator = _Generator
TYPE_CHECKING = _TYPE_CHECKING

T = _TypeVar("T")


@dataclass
class Config:
    general: GeneralConfig = None
    openai: OpenAIConfig = None
    server: ServerConfig = None
    upload: UploadConfig = None
    middleware: MiddlewareConfig = None
    db: DBConfig = None
    cache: CacheConfig = None

    @classmethod
    def parse(cls: _Type[Config], json_data: dict) -> Config:
        return from_dict(
            data_class=cls, data=json_data, config=dacite_config(check_types=False)
        )


@dataclass(slots=True)
class GeneralConfig:
    timezone: float = 0


@dataclass(slots=True)
class CacheConfig:
    general: GeneralCacheConfig = None
    unused_id: UnusedIDConfig = None


@dataclass(slots=True)
class GeneralCacheConfig:
    maxsize: int = 0
    ttl: int = 0


@dataclass(slots=True)
class UnusedIDConfig:
    maxsize: int = 0
    ttl: int = 0


@dataclass(slots=True)
class DBConfig:
    event: DBConfigEvent = None
    file: DBConfigFile = None


@dataclass(slots=True)
class DBConfigEvent:
    path: str = ""


@dataclass(slots=True)
class DBConfigFile:
    path: str = ""


@dataclass(slots=True)
class OpenAIConfig:
    api_key: str = ""
    base_url: str = ""
    db_dir: str = ""


@dataclass(slots=True)
class ServerConfig:
    host: str = "0.0.0.0"
    port: int = 8080
    workers: int = 1


@dataclass(slots=True)
class UploadConfig:
    dir = "./upload"
    allowed = None
    max_size = 20


@dataclass(slots=True)
class MiddlewareConfig:
    cors: CORSConfig = None


@dataclass(slots=True)
class CORSConfig:
    allow_origins: _List[str]
    allow_credentials: bool
    allow_methods: _List[str]
    allow_headers: _List[str]
    expose_headers: _List[str]
    max_age: int

    def to_dict(self) -> _Dict[str, _Any]:
        return asdict(self)


@dataclass
class Response:
    err_code: int = 0
    err_msg: str = ""
    data: _Any = None

    def to_dict(self) -> _Dict[str, _Any]:
        return asdict(self)


@dataclass(slots=True)
class FileMetadata:
    file_id: str
    file_hash: str
    file_path: str
    file_name: str
    file_size: int
    upload_id: str


@dataclass(slots=True)
class EventMetadata:
    event_id: str
    type: str
    status: str
    detail: dict

    def to_dict(self) -> _Dict[str, _Any]:
        return asdict(self)
