# 知行研修 · 学员留存迁移

为知行研修18人运营组记录每个队列的学习轨迹、固定周报口径，并将留存与迁移模型交由运营复核后归档。

## 使用场景

上游 `learning_events_202611.csv` 包含去标识学员学习事件。团队原先手动合并报名表与学习表，入组周口径常变、漏记流失、跨阶段跳转无法解释。本项目替代事件校验、队列口径、留存计算、迁移复核这一段，下游课程运营组据此讨论服务改进。数据全部模拟，不连接真实学员。

## 快速启动

```sh
cp .env.example .env
docker compose up -d --build --wait
docker compose exec -T backend python -m scripts.seed_demo
```

访问 http://localhost:18210 。后端 http://localhost:19210/docs 。PostgreSQL映射17710；Redis、worker不映射端口。恰好 frontend/backend/worker/db/redis 五服务及健康检查，独立命名卷保存数据库、Redis队列和共享导出产物。清理测试数据：`docker compose down -v --remove-orphans`。

| 账号 | 角色 | 权限 |
|---|---|---|
| admin@zhixing.test | admin / 运营复核人 | 全部数据、批准/退回复核、审计 |
| analyst@zhixing.test | analyst / 研修分析员 | 导入事件、保存口径、运行、提交复核、生成报告 |
| viewer@zhixing.test | viewer / 课程观察员 | 查看五类实体、下载已批准报告 |

统一演示密码 `Study2026!`。JWT为HS256，密码PBKDF2；开发示例密钥应在公开部署前通过JWT_SECRET配置。

## 一天的工作剧本

1. 09:00 研修分析员登录，核查900条学习事件与120名学员。
2. 09:05 打开学习事件台账，核验 `learning_events_202611.csv` 的事件编号、周次与序号。
3. 09:10 定义按首次观测周入组的队列，截止第5周，明确是否把结业纳入成功留存。
4. 09:12 提交运行；Redis接收任务，独立worker计算并持久化结果。
5. 09:15 对照三组队列的周留存矩阵与四状态迁移概率。
6. 09:20 记录内部缺测、右删失与齐次马尔可夫假设，提交口径复核。
7. 09:25 运营复核人批准或退回；重复审批返回409。
8. 09:30 根据批准记录生成报告，课程观察员下载含人数、分母、删失、计数与校验哈希的CSV。

## 核心算法与口径

事件列：event_id,learner_id,week,state,sequence。同学员同周取最大sequence；重复事件编号、相同学员周次序号、终态后回退均拒绝，最多5000行。

周留存：首次观测周定义队列，分母仅包括截止日已经达到该队列年龄的成员；超过观察截止日记右删失，分母0、留存率空值。内部未观测周独立计missing，既不前填也不当流失，该格留存率不发布。active计留存，include_completed可纳入completed。所有eligible/observed/active/missing/censored在结果中保存。

迁移：仅使用有相邻日历周观测的状态对估计计数及行归一概率，completed和lost为吸收态。Q为active/dormant子矩阵，N=(I-Q)^-1，期望到达终态前周数为N的行和（包含当前周），吸收概率为N×R。Q谱半径≥1时显式返回不可识别，不输出伪造的有限期望。模型假设齐次一阶迁移；模拟分布不能替代真实课程效果研究。

## 技术与结构

| 层 | 技术 |
|---|---|
| 前端 | React18 / TypeScript / Vite6 / Nginx1.28 |
| 后端 | Python3.12 / FastAPI / psycopg3 / NumPy |
| 持久化 | PostgreSQL16中五业务表、users、audit；每表id主键及JSON文本payload |
| 异步 | Redis7.4队列、独立Python worker、心跳健康检查 |

`backend/src/{routes,controllers,services,models,schemas,middlewares,utils,constants,config}` 分离职责；`frontend/src/{api,stores,types,components/common,hooks,pages,router,utils,constants}` 构成六个业务页及登录页。相同RetentionMatrix组件用于总览和结果页。

共享枚举：后端 `src/constants/enums.py` Role/RunStatus/ReviewStatus，状态 `src/constants/states.py`；前端 `src/constants/enums.ts` 的roleLabels/runLabels/states。模型 `models/entities.py`、schema `schemas/entities.py`、服务与路由均使用这些口径。

环境变量：DATABASE_URL、REDIS_URL、JWT_SECRET、SEED_DEMO、TASK_MODE、ARTIFACT_DIR，Compose端口/命名配置见.env.example。SEED_DEMO默认true，启动seed失败记录日志；自然键insert-only幂等且保留用户修改。演示数据900条、120人、6周，seed无随机漂移。

本地开发：后端 `pip install -r requirements.txt && uvicorn src.main:app --reload`（数据库/Redis配置到运行中的服务）；前端 `npm install && npm run dev`，开发时需配置Vite的/api代理或使用生产Nginx。持久化表结构在backend/migrations/001_initial.sql。

## 边界

Redis列表使用阻塞弹出；worker进程被强杀时已出队任务无自动恢复，需要重新提交。未实现生产级任务重试、多人同时编辑的乐观锁、数据库迁移回滚。默认账号仅用于本地演示。CSV下载对公式前缀做保护。审计不记录密码和JWT。

## 验收资料

真实容器、HTTP、独立算法oracle及浏览器证据位于批次 `test-artifacts/gb-2201/`，不混入源码目录。

## License

MIT，见LICENSE。
