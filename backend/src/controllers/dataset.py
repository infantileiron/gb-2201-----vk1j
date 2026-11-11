from src.services import dataset as service
from src.services import ingest
def list_items(): return service.list_datasets()
def detail(id): return service.detail(id)
def create(data): return service.create(data)
def merge(id,data,user): return ingest.merge_batch(id,data,user)
def batches(id): return ingest.list_batches(id)
