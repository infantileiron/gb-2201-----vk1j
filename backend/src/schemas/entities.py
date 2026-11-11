from pydantic import BaseModel,Field
from typing import Literal
class LoginInput(BaseModel):
 email:str
 password:str
class DatasetInput(BaseModel):
 name:str=Field(min_length=2,max_length=100)
 source:str=Field(default="learning_events_202611.csv",max_length=100)
 csv_text:str=Field(min_length=20,max_length=1000000)
class RenameDataset(BaseModel):
 name:str=Field(min_length=2,max_length=100)
class IngestInput(BaseModel):
 source:str=Field(default="补发事件批次",max_length=100)
 csv_text:str=Field(min_length=20,max_length=1000000)
class CohortDefinitionInput(BaseModel):
 name:str=Field(min_length=2,max_length=100)
 dataset_id:str
 observation_end:int=Field(default=5,ge=1,le=52)
 include_completed:bool=False
class RunInput(BaseModel):
 cohort_id:str
class ReviewInput(BaseModel):
 run_id:str
 comment:str=Field(min_length=5,max_length=2000)
class DecisionInput(BaseModel):
 status:Literal["approved","rejected"]
 comment:str=Field(min_length=5,max_length=2000)
class ReportInput(BaseModel):
 run_id:str
 review_id:str
 title:str=Field(min_length=2,max_length=100)
