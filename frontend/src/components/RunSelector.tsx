import type {Run} from '../types/entities';
export default function RunSelector({runs,value,onChange}:{runs:Run[];value:string;onChange:(s:string)=>void}){return <label className="select-label">选择计算档案<select value={value} onChange={e=>onChange(e.target.value)}>{runs.map(r=><option key={r.id} value={r.id}>{r.id} · {r.status} · 数据v{r.dataset_version||1}</option>)}</select></label>}
