from src.services import cohort as service
def list_items(): return service.list_cohorts()
def create(data): return service.create(data)
