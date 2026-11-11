import random
from src.utils import repository as repo
from src.utils.identity import now
from src.utils.security import hash_password
from src.services.statistics import analyze

def demo_rows():
 rng=random.Random(2201);rows=[];seq=0
 for learner in range(120):
  start=learner%3;state='active'
  for week in range(start,6):
   if week>start and state not in ('completed','lost'):
    u=rng.random()
    state=('completed' if u<.14 else 'lost' if u<.23 else 'dormant' if u<.45 else 'active')
   seq+=1;rows.append({'event_id':f'ev-{seq:04d}','learner_id':f'ZX-{learner+1:03d}','week':week,'state':state,'sequence':10})
 # 600 weekly observations + 300 earlier event records = 900; same terminal state preserves consistency.
 for r in list(rows)[:300]:
  seq+=1;rows.append({**r,'event_id':f'ev-{seq:04d}','sequence':1})
 return rows

def seed():
 repo.init_db()
 for role,name in [('admin','运营复核人'),('analyst','研修分析员'),('viewer','课程观察员')]:
  email=f'{role}@zhixing.test'
  repo.put('users',{'id':email,'email':email,'name':name,'role':role,'password_hash':hash_password('Study2026!')},insert_only=True)
 rows=demo_rows()
 repo.put('datasets',{'id':'ds-learning','name':'11月研修学习事件 · 900条','source':'learning_events_202611.csv','rows':rows,'created_at':now()},insert_only=True)
 repo.put('cohorts',{'id':'cohort-weekly','name':'按首次观测周入组 · 活跃口径','dataset_id':'ds-learning','observation_end':5,'include_completed':False,'created_at':now()},insert_only=True)
 repo.put('runs',{'id':'run-baseline','cohort_id':'cohort-weekly','status':'completed','result':analyze(rows),'error':'','created_at':now()},insert_only=True)
 repo.put('reviews',{'id':'review-baseline','run_id':'run-baseline','comment':'模拟数据口径已核对，缺测分母与终态假设须随报告披露。','status':'approved','reviewer':'admin@zhixing.test','created_at':now()},insert_only=True)
 repo.put('reports',{'id':'report-baseline','run_id':'run-baseline','review_id':'review-baseline','title':'11月学员迁移复核档案','created_at':now()},insert_only=True)
 return {t:len(repo.all_rows(t)) for t in ('users','datasets','cohorts','runs','reviews','reports')}
