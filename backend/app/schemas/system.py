from datetime import datetime
from typing import Literal

from pydantic import Field

from app.schemas.common import APIModel


class HealthData(APIModel):
    status: Literal["ok"]
    database: Literal["connected"]
    location_count: int = Field(ge=0)
    timestamp: datetime

