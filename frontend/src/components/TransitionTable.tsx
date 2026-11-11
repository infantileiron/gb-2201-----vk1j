import type {Run} from '../types/entities';
import {stateLabels} from '../constants/enums';
import {percent,decimal} from '../utils/format';
export default function TransitionTable({run}:{run:Run}){const m=run.result.markov;return <><div className="table-scroll"><table><thead><tr><th>本周 → 下周</th>{stateLabels.map(x=><th key={x}>{x}</th>)}</tr></thead><tbody>{m.matrix.map((row,i)=><tr key={i}><th>{stateLabels[i]}</th>{row.map((v,j)=><td key={j}>{percent(v)}<small>{m.counts[i][j]} 次观测迁移</small></td>)}</tr>)}</tbody></table></div><p className="annotation">活跃 / 休眠的预期剩余周数：{decimal(m.expected_weeks?.[0])} / {decimal(m.expected_weeks?.[1])}。相邻周迁移对：{run.result.markov.counts.flat().reduce((a,b)=>a+b,0)}。{m.warning}</p></>}
