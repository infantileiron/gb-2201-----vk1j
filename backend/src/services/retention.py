from collections import defaultdict
from src.constants.states import STATES,TERMINAL

def weekly_snapshots(rows,end):
 """Use last sequence within each observed week. Missing weeks remain unobserved."""
 by=defaultdict(dict);keys=set()
 for r in rows:
  key=(r['learner_id'],r['week'],r['sequence'])
  if key in keys:raise ValueError('同一学员同周的事件序号必须唯一')
  keys.add(key)
  if r['state'] not in STATES:raise ValueError('未知状态')
  if r['week']>end:continue
  old=by[r['learner_id']].get(r['week'])
  if old is None or r['sequence']>old['sequence']:by[r['learner_id']][r['week']]=r
 for person,weeks in by.items():
  terminal=None
  for week,r in sorted(weeks.items()):
   if terminal is not None and r['state']!=terminal:raise ValueError(f'{person}在终态后出现状态回退')
   if r['state'] in TERMINAL:terminal=r['state']
 return by

def retention_matrix(snapshots,end,include_completed=False):
 cohorts=defaultdict(list)
 for person,weeks in snapshots.items():
  if weeks:cohorts[min(weeks)].append(person)
 result=[]
 for start,people in sorted(cohorts.items()):
  cells=[]
  for age in range(end+1):
   week=start+age;observed=[snapshots[p][week]['state'] for p in people if week in snapshots[p]] if week<=end else []
   active=sum(s=='active' or include_completed and s=='completed' for s in observed)
   cells.append({'age':age,'calendar_week':week,'eligible':len(people) if week<=end else 0,'observed':len(observed),'active':active,'missing':len(people)-len(observed) if week<=end else 0,'censored':0 if week<=end else len(people),'retention':active/len(people) if week<=end and len(observed)==len(people) else None})
  result.append({'cohort_week':start,'size':len(people),'cells':cells})
 return result
