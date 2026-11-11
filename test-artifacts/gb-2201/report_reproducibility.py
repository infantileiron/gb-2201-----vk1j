"""已批准报告在台账合并后仍按原数据复现的端到端验证（纯标准库 + sqlite）。"""
import os, sys, tempfile, io, csv
tmp = tempfile.mkdtemp()
os.environ['DATABASE_URL'] = 'sqlite:///' + tmp + '/r.sqlite'
os.environ['SEED_DEMO'] = 'false'
os.environ['TASK_MODE'] = 'inline'
os.environ['ARTIFACT_DIR'] = tmp + '/artifacts'
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'backend')))
src = open(os.path.join(os.path.dirname(__file__), 'ingest_acceptance.py')).read()
head = src.split('from src.utils import repository as repo')[0]
g = {'__file__': os.path.join(os.path.dirname(__file__), 'ingest_acceptance.py')}
exec(head, g)

from src.utils import repository as repo
from src.services import run as run_service, review as review_service, report as report_service, ingest

repo.init_db()
rows = [
    {'event_id': 'e1', 'learner_id': 'L1', 'week': 0, 'state': 'active', 'sequence': 10},
    {'event_id': 'e2', 'learner_id': 'L1', 'week': 1, 'state': 'active', 'sequence': 10},
    {'event_id': 'e3', 'learner_id': 'L2', 'week': 0, 'state': 'active', 'sequence': 10},
    {'event_id': 'e4', 'learner_id': 'L2', 'week': 1, 'state': 'dormant', 'sequence': 10},
    {'event_id': 'e5', 'learner_id': 'L3', 'week': 0, 'state': 'active', 'sequence': 10},
    {'event_id': 'e6', 'learner_id': 'L3', 'week': 1, 'state': 'active', 'sequence': 10},
]
repo.put('datasets', {'id': 'ds', 'name': 't', 'source': 'b', 'rows': rows,
                      'created_at': 't0', 'version': 1, 'versions': [], 'quarantined': []})
repo.put('cohorts', {'id': 'c', 'name': 'k', 'dataset_id': 'ds',
                     'observation_end': 5, 'include_completed': False, 'created_at': 't0'})
run1 = run_service.execute(repo.put('runs', {'id': 'run1', 'cohort_id': 'c', 'status': 'queued',
                                             'result': {}, 'error': '', 'created_at': 't1'})['id'])
assert run1['dataset_version'] == 1 and run1['result']['learners'] == 3
review_service.create(type('R', (), {'run_id': 'run1', 'comment': '口径核验通过，可以批准。'})(),
                      {'email': 'admin@zhixing.test'})
review_service.decide([r for r in repo.all_rows('reviews')][0]['id'],
                      type('D', (), {'status': 'approved', 'comment': '批准归档。'})(),
                      {'email': 'admin@zhixing.test'})
rpt = report_service.create(type('P', (), {'run_id': 'run1', 'review_id': [r for r in repo.all_rows('reviews')][0]['id'],
                                           'title': '归档报告'})())
csv_before = report_service.download(rpt['id'])

# 台账合并合法迟到事件 → v2
class In:
    def __init__(self, t): self.csv_text = t; self.source = 'late'
ingest.merge_batch('ds', In('event_id,learner_id,week,state,sequence\n'
                            'e7,L4,0,active,10\ne8,L4,1,active,10\n'),
                   {'email': 'analyst@zhixing.test'})
assert repo.get('datasets', 'ds')['version'] == 2

# 再跑一个新分析：4 名学员
run2 = run_service.execute(repo.put('runs', {'id': 'run2', 'cohort_id': 'c', 'status': 'queued',
                                             'result': {}, 'error': '', 'created_at': 't2'})['id'])
assert run2['dataset_version'] == 2 and run2['result']['learners'] == 4

# 旧报告下载内容必须与合并前完全一致（固定引用 v1 快照）
csv_after = report_service.download(rpt['id'])
assert csv_before == csv_after, '已批准报告内容在合并后发生变化'
parsed = list(csv.reader(io.StringIO(csv_after.lstrip('﻿'))))
assert ['reproduced_from_dataset_version', '1'] in parsed
assert any(line and line[0] == 'reproduced_from_dataset_checksum' for line in parsed)
print('PASS 已批准报告合并前后字节一致，固定复现 v1；新运行使用 v2（4 名学员）')
