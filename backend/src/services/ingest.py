"""补发/更正事件向原台账合并。

口径：
- 相同事件（event_id 且 learner/week/state/sequence 完全一致）重复送达 → 幂等跳过，不新增。
- 同一 event_id 但内容冲突 → 隔离该事件并记录原因，不污染台账。
- 合法新事件（含迟到的历史周事件）→ 并入台账，参与后续重算。
- 整批在单事务内处理：任一校验失败全部回滚，不留半批数据。
"""
import csv, io, hashlib, json
from src.models.entities import IngestBatch
from src.utils import repository as repo
from src.utils.identity import new_id, now
from src.constants.states import STATES

REQUIRED_COLUMNS = {'event_id', 'learner_id', 'week', 'state', 'sequence'}
MAX_ROWS = 5000

def checksum(rows):
    return hashlib.sha256(json.dumps(rows, sort_keys=True, ensure_ascii=False).encode()).hexdigest()

def parse_csv(csv_text):
    """解析并逐行做字段级校验；任何非法行都抛 ValueError，调用方整体放弃。"""
    reader = csv.DictReader(io.StringIO(csv_text.lstrip("﻿")))
    if not REQUIRED_COLUMNS.issubset(reader.fieldnames or []):
        raise ValueError('CSV需要event_id,learner_id,week,state,sequence列')
    rows, seen = [], set()
    for n, r in enumerate(reader, 2):
        if n > MAX_ROWS + 1:
            raise ValueError('最多5000个事件')
        try:
            week = int(r['week']); sequence = int(r['sequence'])
            if not 0 <= week <= 52 or not 0 <= sequence <= 100000 \
               or r['state'] not in STATES \
               or not r['learner_id'].strip() or not r['event_id'].strip() \
               or r['event_id'] in seen:
                raise ValueError()
        except (TypeError, ValueError):
            raise ValueError(f'第{n}行周次、状态、事件编号或序号无效')
        seen.add(r['event_id'].strip())
        rows.append({'event_id': r['event_id'].strip(),
                     'learner_id': r['learner_id'].strip(),
                     'week': week, 'state': r['state'], 'sequence': sequence})
    if not rows:
        raise ValueError('批次内没有可接收的事件')
    return rows

def _row_signature(row):
    return (row['learner_id'], row['week'], row['state'], row['sequence'])

def plan_merge(existing_rows, incoming_rows):
    """纯函数式合并规划，便于测试。返回 (合并后行, 统计, 隔离明细)。"""
    by_id = {r['event_id']: r for r in existing_rows}
    merged = [dict(r) for r in existing_rows]
    duplicated = accepted = 0
    quarantined_events = []
    for row in incoming_rows:
        old = by_id.get(row['event_id'])
        if old is None:
            merged.append(dict(row)); by_id[row['event_id']] = row; accepted += 1
        elif _row_signature(old) == _row_signature(row):
            duplicated += 1
        else:
            quarantined_events.append({
                'event_id': row['event_id'],
                'incoming': dict(row),
                'existing': dict(old),
                'reason': '同一事件编号内容冲突：learner_id/week/state/sequence 与台账记录不一致，已隔离待人工核对',
            })
    return merged, {'duplicated': duplicated, 'accepted': accepted,
                    'quarantined': len(quarantined_events)}, quarantined_events

def list_batches(dataset_id=None):
    items = repo.all_rows('ingest_batches')
    if dataset_id:
        items = [b for b in items if b['dataset_id'] == dataset_id]
    return items

def get_batch(id):
    return repo.get('ingest_batches', id)

def _received_count(csv_text):
    lines = [ln for ln in csv_text.splitlines() if ln.strip()]
    return max(0, len(lines) - 1)

def _record_failed(batch_id, dataset_id, source, received, reason, actor):
    """事务回滚后在独立写入中保留失败批次，供页面追溯；不改动台账。"""
    try:
        repo.put('ingest_batches', IngestBatch(
            id=batch_id, dataset_id=dataset_id, source=source, status='failed',
            created_at=now(), received=received, failure_reason=reason, actor=actor))
    except Exception:
        pass

def merge_batch(dataset_id, data, user):
    """向指定台账合并一批补发事件；整批成功或整批失败（事务回滚）。"""
    batch_id = new_id('batch')
    actor = user.get('email', 'anonymous') if user else 'anonymous'
    source = getattr(data, 'source', '补发事件') or '补发事件'
    try:
        incoming = parse_csv(data.csv_text)
    except ValueError as exc:
        # 解析阶段失败：不触碰台账，仅留一条 failed 批次记录用于页面追溯
        _record_failed(batch_id, dataset_id, source,
                       _received_count(data.csv_text), str(exc), actor)
        raise
    try:
        with repo.transaction() as (conn, q):
            dataset = repo.tx_get(conn, q, 'datasets', dataset_id)
            existing = dataset['rows']
            if len(existing) + len(incoming) > MAX_ROWS:
                raise ValueError(f'合并后事件将超过{MAX_ROWS}条上限，本批已整体放弃')
            merged, stats, q_events = plan_merge(existing, incoming)
            # 合并后的台账必须仍满足全局口径：同学员同周序号唯一、终态后不回退
            from src.services.retention import weekly_snapshots
            weekly_snapshots(merged, 52)
            version_before = dataset.get('version', 1)
            version_after = version_before + (1 if stats['accepted'] > 0 else 0)
            if stats['accepted'] > 0:
                # 保存合并前版本的不可变快照元数据；行级复现由各 run 的 snapshot_rows 保证
                dataset.setdefault('versions', []).append({
                    'version': version_before,
                    'checksum': checksum(existing),
                    'row_count': len(existing),
                    'archived_at': now()})
                dataset['rows'] = merged
                dataset['version'] = version_after
            dataset.setdefault('quarantined', [])
            # 台账隔离区按 event_id 去重：同一冲突事件重复送达只更新一条，不重复累积；
            # 每次送达的完整隔离明细仍随批次记录（ingest_batches.quarantined_events）保留。
            q_index = {q['event_id']: i for i, q in enumerate(dataset['quarantined'])}
            for ev in q_events:
                record = {'batch_id': batch_id, 'archived_at': now(), **ev}
                if ev['event_id'] in q_index:
                    dataset['quarantined'][q_index[ev['event_id']]] = record
                else:
                    q_index[ev['event_id']] = len(dataset['quarantined'])
                    dataset['quarantined'].append(record)
            repo.tx_put(conn, q, 'datasets', dataset)
            batch = repo.tx_put(conn, q, 'ingest_batches', IngestBatch(
                id=batch_id, dataset_id=dataset_id, source=source,
                status='applied', created_at=now(),
                received=len(incoming), duplicated=stats['duplicated'],
                accepted=stats['accepted'], quarantined=stats['quarantined'],
                version_before=version_before, version_after=version_after,
                quarantined_events=q_events, actor=actor))
        return batch
    except ValueError as exc:
        # 事务已整体回滚（台账与批次写入都不生效），在事务外补记失败原因
        _record_failed(batch_id, dataset_id, source, len(incoming), str(exc), actor)
        raise
