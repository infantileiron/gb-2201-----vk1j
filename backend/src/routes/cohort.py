from fastapi import APIRouter,Depends
from src.controllers import cohort as controller
from src.schemas.entities import CohortDefinitionInput
from src.services.auth import current,editor,admin
router=APIRouter(prefix="/cohorts",tags=["cohorts"])
@router.get("")
def list_items(user=Depends(current)): return controller.list_items()
@router.post("",status_code=201)
def create(data:CohortDefinitionInput,user=Depends(editor)): return controller.create(data)
