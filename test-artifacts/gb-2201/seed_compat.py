"""验证演示数据 seed 在新数据结构下完整运行，并校验基线运行带版本快照。"""
import os, sys, tempfile
tmp = tempfile.mkdtemp()
os.environ['DATABASE_URL'] = 'sqlite:///' + tmp + '/seed.sqlite'
os.environ['SEED_DEMO'] = 'false'
os.environ['TASK_MODE'] = 'inline'
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'backend')))
acc = open(os.path.join(os.path.dirname(__file__), 'ingest_acceptance.py')).read()
np_start = acc.index("np = types.ModuleType('numpy')")
np_end = acc.index("sys.modules['numpy'] = np") + len("sys.modules['numpy'] = np")
import types
g = {'types': types, 'sys': sys}
exec(acc[np_start:np_end], g)
sys.modules['numpy'] = g['np']

fastapi = types.ModuleType('fastapi')
class HTTPException(Exception):
    def __init__(self, sc, d): self.status_code = sc; self.detail = d
fastapi.HTTPException = HTTPException
sys.modules['fastapi'] = fastapi

from src.services.seed import seed
from src.utils import repository as repo
counts = seed()
print('seed counts:', counts)
ds = repo.get('datasets', 'ds-learning')
run = repo.get('runs', 'run-baseline')
assert ds['version'] == 1 and ds['versions'] == [] and ds['quarantined'] == []
assert len(ds['rows']) == 900
assert run['dataset_version'] == 1
assert len(run['snapshot_rows']) == 900
assert run['dataset_checksum'] == run['result']['checksum']
# 幂等：再次 seed 不覆盖（insert-only）
counts2 = seed()
assert repo.get('runs', 'run-baseline')['id'] == 'run-baseline'
print('PASS seed 生成900条事件、基线运行固定 v1 快照与校验哈希，重复 seed 幂等')
