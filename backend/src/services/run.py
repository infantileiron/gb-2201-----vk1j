from src.models.entities import TransitionRun
from src.utils import repository as repo
from src.utils.identity import new_id, now
from src.services.statistics import analyze
from src.config.settings import TASK_MODE, REDIS_URL, ARTIFACT_DIR
import json
def list_runs(): return repo.all_rows("runs")
def execute(id):
    run=repo.get("runs",id)
    if run["status"] in ("running","completed"): return run
    run["status"]="running"; repo.put("runs",run)
    try:
        exp=repo.get("cohorts",run["cohort_id"])
        dataset=repo.get("datasets",exp["dataset_id"])
        run["result"]=analyze(dataset["rows"],exp["observation_end"],exp["include_completed"])
        ARTIFACT_DIR.mkdir(parents=True,exist_ok=True)
        (ARTIFACT_DIR / (id+".json")).write_text(json.dumps(run["result"],ensure_ascii=False))
        run["status"]="completed"
    except Exception as exc:
        run["status"]="failed"; run["error"]=str(exc)
    return repo.put("runs",run)
def create(data):
    repo.get("cohorts",data.cohort_id)
    if sum(r["status"] in ("queued","running") for r in repo.all_rows("runs"))>=10: raise ValueError("运行队列已满，请等待已有任务完成")
    run=repo.put("runs",TransitionRun(new_id("run"),data.cohort_id,created_at=now()))
    if TASK_MODE=="inline": return execute(run["id"])
    try:
        import redis
        redis.Redis.from_url(REDIS_URL).rpush("cohort-flow:jobs",run["id"])
    except Exception:
        run["status"]="failed"; run["error"]="队列不可用，请恢复Redis后重新提交"
        repo.put("runs",run)
        raise ValueError(run["error"])
    return run
