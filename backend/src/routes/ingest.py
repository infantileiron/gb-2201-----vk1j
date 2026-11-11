from fastapi import APIRouter,Depends
from src.services.ingest import list_batches
from src.services.auth import current
router=APIRouter(prefix="/ingest-batches",tags=["ingest-batches"])
@router.get("")
def all_batches(user=Depends(current)): return list_batches()
