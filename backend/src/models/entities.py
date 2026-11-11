from dataclasses import dataclass,field
from typing import Any
@dataclass
class EventDataset:
 id:str
 name:str
 source:str
 rows:list[dict]
 created_at:str=""
 version:int=1
 # 每次成功合并后保留的历史版本快照，保证旧分析可按原数据复现
 versions:list[dict]=field(default_factory=list)
 # 历次批次中被隔离的事件及其原因，始终随台账保留
 quarantined:list[dict]=field(default_factory=list)
@dataclass
class IngestBatch:
 id:str
 dataset_id:str
 source:str
 status:str                 # applied / failed
 created_at:str
 received:int=0             # 本批送达到行数
 duplicated:int=0           # 相同事件重复送达，未新增
 accepted:int=0             # 合法（含迟到）并入台账的事件
 quarantined:int=0          # 同编号内容冲突等被隔离的事件
 version_before:int=0
 version_after:int=0
 quarantined_events:list[dict]=field(default_factory=list)
 failure_reason:str=""
 actor:str=""
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
 # 运行实际使用的数据集版本与行快照；旧运行不随后续合并改变
 dataset_version:int=0
 dataset_checksum:str=""
 snapshot_rows:list[dict]=field(default_factory=list)
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
