import csv,io
from fastapi import HTTPException
from src.models.entities import PublishedReport
from src.config.settings import ARTIFACT_DIR
from src.utils import repository as repo
from src.utils.identity import new_id,now
def safe_cell(value):
    return "'"+value if isinstance(value,str) and value.lstrip().startswith(("=","+","-","@")) else value
def list_reports(): return repo.all_rows("reports")
def create(data):
    run,review=repo.get("runs",data.run_id),repo.get("reviews",data.review_id)
    if review["status"]!="approved" or review["run_id"]!=run["id"] or run["status"]!="completed": raise ValueError("报告必须引用该运行已通过的复核")
    report=repo.put("reports",PublishedReport(new_id("rpt"),data.run_id,data.review_id,data.title,now()))
    ARTIFACT_DIR.mkdir(parents=True,exist_ok=True)
    (ARTIFACT_DIR/(report["id"]+".csv")).write_text(download(report["id"]),encoding="utf-8")
    return report
def download(id):
    report=repo.get("reports",id); run=repo.get("runs",report["run_id"])
    if repo.get("reviews",report["review_id"])["status"]!="approved": raise HTTPException(403,"复核未通过")
    r=run['result'];out=io.StringIO();writer=csv.writer(out)
    writer.writerow(['report','cohort_week','age','eligible','observed','active','missing','censored','retention','checksum'])
    for cohort in r['cohorts']:
        for c in cohort['cells']:writer.writerow([safe_cell(report['title']),cohort['cohort_week'],c['age'],c['eligible'],c['observed'],c['active'],c['missing'],c['censored'],c['retention'],r['checksum']])
    writer.writerow([]);writer.writerow(['from_state','to_state','transition_count','probability'])
    m=r['markov']
    for i,state in enumerate(m['states']):
        for j,target in enumerate(m['states']):writer.writerow([state,target,m['counts'][i][j],m['matrix'][i][j]])
    return '\ufeff'+out.getvalue()
