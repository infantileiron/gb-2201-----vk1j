import hashlib,json
from src.services.retention import weekly_snapshots,retention_matrix
from src.services.markov import transition_analysis

def analyze(rows,end=5,include_completed=False):
 snapshots=weekly_snapshots(rows,end)
 if len(snapshots)<2:raise ValueError('至少需要2名学员')
 cohorts=retention_matrix(snapshots,end,include_completed)
 markov=transition_analysis(snapshots)
 return {'learners':len(snapshots),'events':sum(r['week']<=end for r in rows),'observation_end':end,'include_completed':include_completed,'cohorts':cohorts,'markov':markov,'checksum':hashlib.sha256(json.dumps(rows,sort_keys=True).encode()).hexdigest(),'limitations':['模拟事件仅用于流程演示','留存分母只包括截止日已达到相应年龄的成员；右删失不记为流失；内部缺测单列且该格留存率不发布','马尔可夫模型假设齐次、一阶迁移；期望为到达completed/lost前的剩余周数，含当前周','只统计相邻周的迁移，不跨缺测周推断迁移']}
