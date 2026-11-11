"""补充边界：失败运行重跑会重新快照最新版本；已完成运行重跑不覆盖快照。"""
import os, sys, tempfile
tmp = tempfile.mkdtemp()
os.environ['DATABASE_URL'] = 'sqlite:///' + tmp + '/edge.sqlite'
os.environ['SEED_DEMO'] = 'false'
os.environ['TASK_MODE'] = 'inline'
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'backend')))
acc = open(os.path.join(os.path.dirname(__file__), 'ingest_acceptance.py')).read()
import types
g = {'types': types, 'sys': sys}
exec(acc[acc.index("np = types.ModuleType('numpy')"):acc.index("sys.modules['numpy'] = np") + len("sys.modules['numpy'] = np")], g)
sys.modules['numpy'] = g['np']
fa = types.ModuleType('fastapi')
class H(Exception):
    def __init__(s, c, d): s.status_code = c; s.detail = d
fa.HTTPException = H; sys.modules['fastapi'] = fa

from src.utils import repository as repo
from src.services import run as run_service, ingest
repo.init_db()
rows = [
    {'event_id': 'e1', 'learner_id': 'L1', 'week': 0, 'state': 'active', 'sequence': 10},
    {'event_id': 'e2', 'learner_id': 'L1', 'week': 1, 'state': 'active', 'sequence': 10},
    {'event_id': 'e3', 'learner_id': 'L2', 'week': 0, 'state': 'active', 'sequence': 10},
    {'event_id': 'e4', 'learner_id': 'L2', 'week': 1, 'state': 'dormant', 'sequence': 10},
]
repo.put('datasets', {'id': 'ds', 'name': 't', 'source': 'b', 'rows': rows,
                      'created_at': 't0', 'version': 1, 'versions': [], 'quarantined': []})
repo.put('cohorts', {'id': 'c', 'name': 'k', 'dataset_id': 'ds',
                     'observation_end': 5, 'include_completed': False, 'created_at': 't0'})
run = run_service.execute(repo.put('runs', {'id': 'r1', 'cohort_id': 'c', 'status': 'queued',
                                           'result': {}, 'error': '', 'created_at': 't1'})['id'])
snap_v1 = run['snapshot_rows']; cs_v1 = run['dataset_checksum']

# 已完成运行再次 execute：直接返回，不覆盖
again = run_service.execute('r1')
assert again['dataset_checksum'] == cs_v1 and again['snapshot_rows'] == snap_v1

# 合并升级到 v2 后，已完成运行仍保持 v1 快照
class In:
    def __init__(self, t): self.csv_text = t; self.source = 's'
ingest.merge_batch('ds', In('event_id,learner_id,week,state,sequence\ne5,L3,0,active,10\ne6,L3,1,active,10\n'), {'email': 'a'})
assert run_service.execute('r1')['dataset_checksum'] == cs_v1

# 失败运行重跑：重新进入计算并快照最新 v2
repo.put('runs', {'id': 'r2', 'cohort_id': 'c', 'status': 'failed', 'result': {},
                  'error': '旧失败', 'created_at': 't2'})
rerun = run_service.execute('r2')
assert rerun['status'] == 'completed' and rerun['dataset_version'] == 2
assert len(rerun['snapshot_rows']) == 6 and rerun['dataset_checksum'] != cs_v1
print('PASS 已完成运行重跑不覆盖快照；失败运行重跑重新快照合并后 v2')
