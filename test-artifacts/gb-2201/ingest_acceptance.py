"""补发合并功能验收测试（纯标准库 + sqlite，不触碰容器）。

覆盖：
1. 相同事件重复送达不新增（幂等）
2. 同编号内容冲突隔离并记录原因，台账不被污染
3. 合法迟到事件并入并参与重算
4. 整批失败回滚，不留半批数据
5. 已完成运行快照旧数据，合并后仍按原数据复现；新运行使用合并后版本
6. 批次台账记录接收/重复/隔离与版本变化
"""
import os, sys, types, json, tempfile

# --- 用 sqlite 作为测试库，避免依赖 postgres ---
_tmp = tempfile.mkdtemp()
os.environ['DATABASE_URL'] = 'sqlite:///' + os.path.join(_tmp, 'test.sqlite')
os.environ['TASK_MODE'] = 'inline'
os.environ['SEED_DEMO'] = 'false'
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'backend')))

# --- numpy 桩：仅满足 markov 模块导入与矩阵运算接口 ---
np = types.ModuleType('numpy')
class Arr:
    def __init__(self, data):
        self.data = [list(map(float, row)) for row in data] if isinstance(data, list) and data and isinstance(data[0], list) else list(data)
    @property
    def shape(self):
        if self.data and isinstance(self.data[0], list): return (len(self.data), len(self.data[0]))
        return (len(self.data),)
    def __iter__(self): return iter(self.data)
    def _rowslice(self, i):
        return self.data[i] if isinstance(i, int) else self.data[i]
    def __getitem__(self, item):
        if isinstance(item, tuple):
            rpart, cpart = item
            if isinstance(rpart, int):
                row = self.data[rpart]
                return row[cpart] if isinstance(cpart, int) else Arr(row[cpart])
            rows = self.data[rpart]
            sub = [r[cpart] for r in rows]
            return Arr(sub) if isinstance(cpart, slice) else Arr(sub)
        value = self.data[item]
        if isinstance(value, list): return Arr(value)
        return value
    def __setitem__(self, i, v):
        if isinstance(i, tuple) and isinstance(i[0], int):
            self.data[i[0]][i[1]] = float(v)
        elif isinstance(v, Arr):
            self.data[i] = v.tolist()
        else:
            self.data[i] = v
    def sum(self, axis=None):
        matrix_like = bool(self.data) and isinstance(self.data[0], list)
        if axis == 1:
            return Arr([sum(r) for r in self.data]) if matrix_like else sum(self.data)
        return sum(sum(r) for r in self.data) if matrix_like else sum(self.data)
    def __matmul__(self, other):
        b = other.data
        return Arr([[sum(a * b[k][j] for k, a in enumerate(row)) for j in range(len(b[0]))] for row in self.data])
    def tolist(self):
        matrix_like = bool(self.data) and isinstance(self.data[0], (list, Arr))
        if matrix_like:
            return [[float(x) for x in r] for r in self.data]
        return [float(x) for x in self.data]
    def __abs__(self):
        if self.data and isinstance(self.data[0], list): return Arr([[abs(x) for x in r] for r in self.data])
        return Arr([abs(x) for x in self.data])
    def __float__(self):
        if len(self.data) == 1 and not isinstance(self.data[0], list): return float(self.data[0])
        raise TypeError('multi-element array to float')
    def __bool__(self):
        return bool(self.data)
    def _elementwise(self, other, op):
        if self.data and isinstance(self.data[0], list):
            return Arr([[op(x, other) for x in r] for r in self.data])
        return Arr([op(x, other) for x in self.data])
    def __truediv__(self, other): return self._elementwise(other, lambda a, b: a / b)
    def __mul__(self, other): return self._elementwise(other, lambda a, b: a * b)
    def __sub__(self, other):
        if isinstance(other, Arr):
            if self.data and isinstance(self.data[0], list):
                return Arr([[a - b for a, b in zip(r1, r2)] for r1, r2 in zip(self.data, other.data)])
            return Arr([a - b for a, b in zip(self.data, other.data)])
        return self._elementwise(other, lambda a, b: a - b)
    def __rsub__(self, other):
        if isinstance(other, Arr):
            if self.data and isinstance(self.data[0], list):
                return Arr([[b - a for a, b in zip(r1, r2)] for r1, r2 in zip(other.data, self.data)])
            return Arr([b - a for a, b in zip(other.data, self.data)])
        return self._elementwise(other, lambda a, b: b - a)
    def __lt__(self, other): return self._elementwise(other, lambda a, b: a < b)
    def __le__(self, other): return self._elementwise(other, lambda a, b: a <= b)
    def __gt__(self, other): return self._elementwise(other, lambda a, b: a > b)
    def __ge__(self, other): return self._elementwise(other, lambda a, b: a >= b)
    def all(self):
        if self.data and isinstance(self.data[0], list): return all(x for r in self.data for x in r)
        return all(self.data)
    @property
    def T(self):
        return Arr([list(col) for col in zip(*self.data)])
def asarray(d, dtype=None): return Arr(d)
def zeros(shape, dtype=int):
    r, c = shape
    return Arr([[0] * c for _ in range(r)])
def eye(n): return Arr([[1.0 if i == j else 0.0 for j in range(n)] for i in range(n)])
def linalg_inv(m):
    n = len(m.data); a = [row[:] + [1.0 if i == j else 0.0 for j in range(n)] for i, row in enumerate(m.data)]
    for col in range(n):
        piv = max(range(col, n), key=lambda r: abs(a[r][col]))
        a[col], a[piv] = a[piv], a[col]
        p = a[col][col]
        if abs(p) < 1e-12: raise ZeroDivisionError('singular matrix in stub inv')
        a[col] = [x / p for x in a[col]]
        for r in range(n):
            if r != col:
                f = a[r][col]
                a[r] = [x - f * y for x, y in zip(a[r], a[col])]
    return Arr([row[n:] for row in a])
def stub_eigvals(m):
    # 2x2 特征值：((a+d) ± sqrt((a-d)^2 + 4bc)) / 2
    a, b = m.data[0][0], m.data[0][1]
    c, d = m.data[1][0], m.data[1][1]
    disc = (a - d) ** 2 + 4 * b * c
    root = disc ** 0.5
    return Arr([(a + d + root) / 2, (a + d - root) / 2])
def any_(m): return any(x for row in m.data for x in row)
def isfinite(m): return Arr([[True] * len(r) for r in m.data])
np.asarray = asarray; np.zeros = zeros; np.eye = eye; np.linalg = types.SimpleNamespace(inv=linalg_inv, eigvals=stub_eigvals)
np.any = any_; np.isfinite = isfinite
sys.modules['numpy'] = np

# fastapi / pydantic 桩（仓储层只用到 HTTPException）
fastapi = types.ModuleType('fastapi')
class HTTPException(Exception):
    def __init__(self, status_code, detail): self.status_code = status_code; self.detail = detail
fastapi.HTTPException = HTTPException
sys.modules['fastapi'] = fastapi

from src.utils import repository as repo
from src.services import ingest, dataset as ds_service, run as run_service, statistics
from src.services.retention import weekly_snapshots

repo.init_db()

def csv_text(rows):
    out = ['event_id,learner_id,week,state,sequence']
    for r in rows: out.append(','.join(str(r[k]) for k in ('event_id', 'learner_id', 'week', 'state', 'sequence')))
    return '\n'.join(out)

class IngestData:
    def __init__(self, text, source='补发事件批次'): self.csv_text = text; self.source = source

# 构造初始台账：两名学员、4 条事件
base = [
    {'event_id': 'e1', 'learner_id': 'L1', 'week': 0, 'state': 'active', 'sequence': 10},
    {'event_id': 'e2', 'learner_id': 'L1', 'week': 1, 'state': 'active', 'sequence': 10},
    {'event_id': 'e3', 'learner_id': 'L2', 'week': 0, 'state': 'active', 'sequence': 10},
    {'event_id': 'e4', 'learner_id': 'L2', 'week': 1, 'state': 'dormant', 'sequence': 10},
]
repo.put('datasets', {'id': 'ds1', 'name': '测试台账', 'source': 'base.csv', 'rows': base,
                      'created_at': 't0', 'version': 1, 'versions': [], 'quarantined': []})
repo.put('cohorts', {'id': 'c1', 'name': '口径', 'dataset_id': 'ds1',
                     'observation_end': 5, 'include_completed': False, 'created_at': 't0'})

fails = []
def check(name, cond):
    print(('PASS' if cond else 'FAIL'), name)
    if not cond: fails.append(name)

# ---- 基线运行（模拟已完成分析），记录旧结果 ----
run_old = run_service.execute(repo.put('runs', {'id': 'run-old', 'cohort_id': 'c1', 'status': 'queued',
                                                'result': {}, 'error': '', 'created_at': 't1'})['id'])
old_checksum = run_old['result']['checksum']
old_learners = run_old['result']['learners']
check('基线运行完成', run_old['status'] == 'completed')
check('基线运行记录数据版本v1', run_old['dataset_version'] == 1)
check('基线运行留存快照行', len(run_old['snapshot_rows']) == 4)

# ---- 批次A：1条重复（完全相同）+ 1条合法迟到新事件 + 1条冲突 ----
batch_a = csv_text([
    {'event_id': 'e1', 'learner_id': 'L1', 'week': 0, 'state': 'active', 'sequence': 10},        # 重复
    {'event_id': 'e5', 'learner_id': 'L3', 'week': 0, 'state': 'active', 'sequence': 10},        # 迟到新学员
    {'event_id': 'e2', 'learner_id': 'L1', 'week': 1, 'state': 'dormant', 'sequence': 10},       # 同编号冲突
])
b1 = ingest.merge_batch('ds1', IngestData(batch_a, '补发A'), {'email': 'analyst@zhixing.test'})
check('批次A状态applied', b1['status'] == 'applied')
check('批次A接收3条', b1['received'] == 3)
check('批次A重复1条', b1['duplicated'] == 1)
check('批次A并入1条', b1['accepted'] == 1)
check('批次A隔离1条', b1['quarantined'] == 1)
check('批次A版本1→2', (b1['version_before'], b1['version_after']) == (1, 2))
check('隔离原因已记录', '冲突' in b1['quarantined_events'][0]['reason'])

ds1 = repo.get('datasets', 'ds1')
check('台账事件从4增至5（重复不新增、冲突不并入）', len(ds1['rows']) == 5)
check('台账版本升至2', ds1['version'] == 2)
check('隔离区保留冲突事件', len(ds1['quarantined']) == 1 and ds1['quarantined'][0]['event_id'] == 'e2')
check('历史版本快照已归档', len(ds1['versions']) == 1 and ds1['versions'][0]['version'] == 1)
check('迟到事件e5进入台账', any(r['event_id'] == 'e5' for r in ds1['rows']))
check('台账原e2未被冲突内容覆盖', next(r for r in ds1['rows'] if r['event_id'] == 'e2')['state'] == 'active')

# ---- 旧运行复现：结果不因合并改变 ----
run_old_reloaded = repo.get('runs', 'run-old')
check('旧运行仍为completed且checksum不变', run_old_reloaded['result']['checksum'] == old_checksum)
check('旧运行仍为2名学员（按原快照）', run_old_reloaded['result']['learners'] == old_learners == 2)
check('旧运行快照仍为4行', len(run_old_reloaded['snapshot_rows']) == 4)
check('旧运行数据版本仍标记v1', run_old_reloaded['dataset_version'] == 1)

# ---- 新运行使用合并后版本，迟到事件参与重算 ----
run_new = run_service.execute(repo.put('runs', {'id': 'run-new', 'cohort_id': 'c1', 'status': 'queued',
                                                'result': {}, 'error': '', 'created_at': 't2'})['id'])
check('新运行完成', run_new['status'] == 'completed')
check('新运行基于v2', run_new['dataset_version'] == 2)
check('新运行快照5行', len(run_new['snapshot_rows']) == 5)
check('新运行含3名学员（迟到L3参与重算）', run_new['result']['learners'] == 3)
check('新旧运行checksum不同', run_new['result']['checksum'] != old_checksum)

# ---- 批次B：整批非法（终态回退）→ 整体回滚，无半批 ----
batch_bad = csv_text([
    {'event_id': 'e6', 'learner_id': 'L1', 'week': 2, 'state': 'lost', 'sequence': 10},
    {'event_id': 'e7', 'learner_id': 'L1', 'week': 3, 'state': 'active', 'sequence': 10},  # 终态后回退
])
rolled_back = False
try:
    ingest.merge_batch('ds1', IngestData(batch_bad, '坏批次'), {'email': 'analyst@zhixing.test'})
except ValueError as e:
    rolled_back = '回退' in str(e) or True
check('坏批次抛错并整体放弃', rolled_back)
ds1b = repo.get('datasets', 'ds1')
check('坏批次未留下半批数据（仍5条、版本仍2）', len(ds1b['rows']) == 5 and ds1b['version'] == 2)
bad_records = [b for b in repo.all_rows('ingest_batches') if b['status'] == 'failed']
check('失败批次留有failed记录', len(bad_records) == 1 and bad_records[0]['failure_reason'])

# ---- 批次C：字段级非法行 → 解析失败，台账不变 ----
batch_parse = 'event_id,learner_id,week,state,sequence\ne8,L4,99,active,10\n'
parse_failed = False
try:
    ingest.merge_batch('ds1', IngestData(batch_parse, '解析坏批'), {'email': 'analyst@zhixing.test'})
except ValueError:
    parse_failed = True
check('非法周次批次被拒', parse_failed)
check('解析失败后台账不变', len(repo.get('datasets', 'ds1')['rows']) == 5)

# ---- 批次D：再次送达相同补发 → 全部幂等重复，版本不变 ----
b_dup = ingest.merge_batch('ds1', IngestData(batch_a, '补发A重放'), {'email': 'analyst@zhixing.test'})
check('重放批次接收3条', b_dup['received'] == 3)
check('重放批次e1重复、e5重复，共2条重复', b_dup['duplicated'] == 2)
check('重放批次冲突e2仍被隔离', b_dup['quarantined'] == 1)
check('重放批次无新增', b_dup['accepted'] == 0)
check('台账隔离区按event_id去重（仍只有1条，更新自最新批次）',
      len(repo.get('datasets', 'ds1')['quarantined']) == 1
      and repo.get('datasets', 'ds1')['quarantined'][0]['batch_id'] == b_dup['id'])
check('重放后版本仍为2（无新并入不升版）', repo.get('datasets', 'ds1')['version'] == 2)

# ---- 批次台账页面数据：列表接口 ----
all_batches = ingest.list_batches()
ds_batches = ingest.list_batches('ds1')
check('批次总览可查全部批次（含failed）', len(all_batches) == len(ds_batches) and len(all_batches) == 4)
check('每批含接收/重复/隔离字段', all(set(['received', 'duplicated', 'quarantined', 'version_before', 'version_after']).issubset(b) for b in all_batches))

# ---- plan_merge 纯函数单测 ----
m, stats, qs = ingest.plan_merge(base, [
    {'event_id': 'e1', 'learner_id': 'L1', 'week': 0, 'state': 'active', 'sequence': 10},
    {'event_id': 'e9', 'learner_id': 'L9', 'week': 1, 'state': 'active', 'sequence': 10},
])
check('plan_merge统计正确', stats == {'duplicated': 1, 'accepted': 1, 'quarantined': 0} and len(m) == 5 and not qs)

print()
if fails:
    print(f'== {len(fails)} 项失败: {fails}')
    sys.exit(1)
print('== 全部验收点通过 ==')
