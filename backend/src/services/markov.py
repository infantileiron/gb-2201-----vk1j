import numpy as np
from src.constants.states import STATES,TERMINAL

def absorbing_summary(counts):
 counts=np.asarray(counts,dtype=float)
 if counts.shape!=(4,4) or np.any(counts<0) or not np.isfinite(counts).all():raise ValueError('迁移计数矩阵无效')
 matrix=np.zeros((4,4))
 for i in range(2):
  total=counts[i].sum()
  if total:matrix[i]=counts[i]/total
  else:matrix[i,i]=1
 matrix[2,2]=matrix[3,3]=1
 q=matrix[:2,:2];radius=float(max(abs(np.linalg.eigvals(q))))
 if radius>=1-1e-10:
  return {'matrix':matrix.tolist(),'expected_weeks':None,'absorption':None,'identifiable':False,'warning':'至少一个暂态无可达终态，期望时间不可识别；未添加平滑伪计数'}
 n=np.linalg.inv(np.eye(2)-q)
 return {'matrix':matrix.tolist(),'expected_weeks':n.sum(axis=1).tolist(),'absorption':(n@matrix[:2,2:]).tolist(),'identifiable':True,'warning':''}
def transition_analysis(snapshots):
 counts=np.zeros((4,4),dtype=int);pairs=0
 for weeks in snapshots.values():
  for week,r in weeks.items():
   if week+1 in weeks:
    counts[STATES.index(r['state']),STATES.index(weeks[week+1]['state'])]+=1;pairs+=1
 return {'states':list(STATES),'counts':counts.tolist(),'adjacent_pairs':pairs,**absorbing_summary(counts)}
