import {useState} from 'react';
import * as api from '../api/datasets';
import {useResource} from '../hooks/useResource';
import {refreshResources} from '../stores/resources';
import {readText} from '../utils/csv';
import PageTitle from '../components/common/PageTitle';
import Notice from '../components/common/Notice';
import StatusBadge from '../components/common/StatusBadge';
import type {User,IngestBatchSummary} from '../types/entities';

export default function Datasets({user}:{user:User}){
  const {data,error}=useResource(api.list,[]);
  const {data:batches}=useResource(api.allBatches,[]);
  const [target,setTarget]=useState('ds-learning');
  const [source,setSource]=useState('补发事件批次');
  const [csv,setCsv]=useState('');
  const [message,setMessage]=useState('');
  const canEdit=user.role!=='viewer';
  const selected=data.find(d=>d.id===target)||data[0];

  async function submit(e:React.FormEvent){
    e.preventDefault();
    if(!selected){setMessage('请先选择要合并的目标台账');return;}
    try{
      const b=await api.merge(selected.id,{source,csv_text:csv});
      setMessage(`批次 ${b.id} 已合并：接收 ${b.received} 条，重复跳过 ${b.duplicated} 条，并入 ${b.accepted} 条，隔离 ${b.quarantined} 条，版本 v${b.version_before} → v${b.version_after}`);
      setCsv('');
      refreshResources();
    }catch(e:any){setMessage(e.message);refreshResources();}
  }

  return <>
    <PageTitle chapter="02" title="学习事件台账" description="补发与更正事件向原台账合并：相同事件重复送达不新增；同编号内容冲突隔离并注明原因；合法迟到事件参与重算。整批失败不留半批数据。"/>
    <Notice error={error||message}/>
    <section className="paper table-scroll">
      <table>
        <thead><tr><th>观测台账</th><th>数据版本</th><th>事件</th><th>学员</th><th>周次</th><th>隔离事件</th></tr></thead>
        <tbody>{data.map(d=><tr key={d.id} className={selected?.id===d.id?'selected-row':''}>
          <td><b>{d.name}</b><small>{d.source} · {d.id}</small></td>
          <td><span className="badge">v{d.version}</span></td>
          <td>{d.row_count}</td><td>{d.learners}</td><td>{d.weeks.join(' / ')}</td>
          <td>{d.quarantine_count}</td>
        </tr>)}</tbody>
      </table>
    </section>

    {canEdit&&<form className="paper form-grid" onSubmit={submit}>
      <h2>向原台账合并补发 / 更正事件</h2>
      <label>目标台账
        <select value={selected?.id||''} onChange={e=>setTarget(e.target.value)}>
          {data.map(d=><option key={d.id} value={d.id}>{d.name}（v{d.version}）</option>)}
        </select>
      </label>
      <label>批次来源<input value={source} onChange={e=>setSource(e.target.value)}/></label>
      <label>选择 CSV 文件<input type="file" accept=".csv" onChange={async e=>{if(e.target.files?.[0])try{setCsv(await readText(e.target.files[0]))}catch(e:any){setMessage(e.message)}}}/></label>
      <label className="wide">CSV 内容<textarea value={csv} onChange={e=>setCsv(e.target.value)} placeholder="event_id,learner_id,week,state,sequence"/></label>
      <button className="primary">校验并整批合并</button>
    </form>}

    <section className="paper table-scroll">
      <h2>批次接收台账（接收 / 重复 / 隔离 / 数据版本）</h2>
      {batches.length===0?<p className="annotation">还没有补发批次。</p>:<table>
        <thead><tr><th>批次</th><th>状态</th><th>来源 / 操作人</th><th>接收</th><th>重复跳过</th><th>并入</th><th>隔离</th><th>版本变化</th><th>时间</th></tr></thead>
        <tbody>{batches.map((b:IngestBatchSummary)=><tr key={b.id}>
          <td><b>{b.id}</b>{b.failure_reason&&<small className="fail-reason">{b.failure_reason}</small>}</td>
          <td><StatusBadge status={b.status}/></td>
          <td>{b.source}<small>{b.actor}</small></td>
          <td>{b.received}</td><td>{b.duplicated}</td><td>{b.accepted}</td><td>{b.quarantined}</td>
          <td>{b.status==='applied'?`v${b.version_before} → v${b.version_after}`:'—'}</td>
          <td><small>{b.created_at}</small></td>
        </tr>)}</tbody>
      </table>}
    </section>

    {batches.some((b:IngestBatchSummary)=>b.quarantined_events?.length>0)&&<section className="paper table-scroll">
      <h2>隔离事件与原因</h2>
      <table>
        <thead><tr><th>事件编号</th><th>批次</th><th>台账原记录</th><th>送达记录</th><th>隔离原因</th></tr></thead>
        <tbody>{batches.flatMap((b:IngestBatchSummary)=>b.quarantined_events.map(q=><tr key={b.id+q.event_id}>
          <td><b>{q.event_id}</b></td>
          <td><small>{b.id}</small></td>
          <td className="cell-event">{q.existing.learner_id} · 第{q.existing.week}周 · {q.existing.state} · seq{q.existing.sequence}</td>
          <td className="cell-event">{q.incoming.learner_id} · 第{q.incoming.week}周 · {q.incoming.state} · seq{q.incoming.sequence}</td>
          <td className="fail-reason">{q.reason}</td>
        </tr>))}</tbody>
      </table>
    </section>}
  </>;
}
