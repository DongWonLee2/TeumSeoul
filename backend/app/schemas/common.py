from typing import Generic, TypeVar

from pydantic import BaseModel, ConfigDict, Field

DataT = TypeVar("DataT")


class APIModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class PaginationMeta(APIModel):
    page: int = Field(ge=1)
    size: int = Field(ge=1, le=100)
    total_items: int = Field(ge=0)
    total_pages: int = Field(ge=0)


class PaginationParams(APIModel):
    page: int = Field(default=1, ge=1)
    size: int = Field(default=20, ge=1, le=100)


class DataResponse(APIModel, Generic[DataT]):
    data: DataT
    meta: PaginationMeta | dict[str, object] | None = None


class ErrorResponse(APIModel):
    detail: str
    code: str
