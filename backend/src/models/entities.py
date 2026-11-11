from dataclasses import dataclass,field
from typing import Any
@dataclass
class EventDataset:
 id:str
 name:str
 source:str
 rows:list[dict]
 created_at:str=""
@dataclass
class CohortDefinition:
 id:str
 name:str
 dataset_id:str
 observation_end:int=5
 include_completed:bool=False
 created_at:str=""
@dataclass
class TransitionRun:
 id:str
 cohort_id:str
 status:str="queued"
 result:dict[str,Any]=field(default_factory=dict)
 error:str=""
 created_at:str=""
@dataclass
class SegmentReview:
 id:str
 run_id:str
 comment:str
 status:str="pending"
 reviewer:str=""
 created_at:str=""
@dataclass
class PublishedReport:
 id:str
 run_id:str
 review_id:str
 title:str
 created_at:str=""
