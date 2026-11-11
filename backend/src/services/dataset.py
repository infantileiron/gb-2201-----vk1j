import csv,io
from dataclasses import asdict
from src.models.entities import EventDataset
from src.utils import repository as repo
from src.utils.identity import new_id,now
from src.constants.states import STATES

def summary(item):
 return {k:v for k,v in item.items() if k!="rows"}|{"row_count":len(item["rows"]),"learners":len({r["learner_id"] for r in item["rows"]}),"weeks":sorted({r["week"] for r in item["rows"]})}
def list_datasets():return [summary(x) for x in repo.all_rows("datasets")]
def detail(id):return repo.get("datasets",id)
def rename(id,data):
 item=repo.get("datasets",id);item['name']=data.name;repo.put('datasets',item);return summary(item)
def create(data):
 reader=csv.DictReader(io.StringIO(data.csv_text.lstrip("\ufeff")))
 if not {'event_id','learner_id','week','state','sequence'}.issubset(reader.fieldnames or []):raise ValueError('CSV需要event_id,learner_id,week,state,sequence列')
 rows=[];seen=set()
 for n,r in enumerate(reader,2):
  if n>5001:raise ValueError('最多5000个事件')
  try:
   week=int(r['week']);sequence=int(r['sequence'])
   if not 0<=week<=52 or not 0<=sequence<=100000 or r['state'] not in STATES or not r['learner_id'].strip() or not r['event_id'].strip() or r['event_id'] in seen:raise ValueError()
  except (TypeError,ValueError):raise ValueError(f'第{n}行周次、状态、事件编号或序号无效')
  seen.add(r['event_id']);rows.append({'event_id':r['event_id'],'learner_id':r['learner_id'].strip(),'week':week,'state':r['state'],'sequence':sequence})
 if len(rows)<4:raise ValueError('至少4条事件')
 # Validation includes terminal-state reversals and ambiguous duplicate sequences.
 from src.services.retention import weekly_snapshots
 weekly_snapshots(rows,52)
 item=EventDataset(new_id('ds'),data.name,data.source,rows,now());repo.put('datasets',item);return summary(asdict(item))
