from src.models.entities import CohortDefinition
from src.utils import repository as repo
from src.utils.identity import new_id,now

def list_cohorts():return repo.all_rows('cohorts')
def create(data):
 repo.get('datasets',data.dataset_id)
 return repo.put('cohorts',CohortDefinition(new_id('cohort'),data.name,data.dataset_id,data.observation_end,data.include_completed,now()))
