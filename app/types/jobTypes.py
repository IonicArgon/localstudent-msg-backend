from enum import Enum
from typing import TypedDict

class JobTypes(Enum):
    CONNECT = 1
    SCRAPE = 2
    FILTER = 3
    DATABASE = 4
    SETTING = 5

class Job(TypedDict):
    job_id: str
    job_type: JobTypes
    job_data: dict

class JobReturn(TypedDict):
    job_id: str
    job_type: JobTypes
    job_return_data: dict