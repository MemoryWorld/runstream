# Runstream

**实验运行流（Runstream）** 是一个**研究原型**课题：把分散在各处的一次次训练 / 评测运行，变成**可管道化摄取、可服务化访问、可被助理程序安全查询**的统一层。动机来自我们与一个**小型平台组**的闲聊——他们同时对接课题组笔记本、共享盘上的 `runs/`、以及偶发的对象存储快照；人工对账「哪次 run 用了哪份 config、指标差多少」成本高，且不适合写死在某个单一训练仓库里。

本仓库**刻意独立**于任何具体模型实现：它假设「运行元数据」会以约定好的 JSON / 目录结构出现（见 `fixtures/example_run/`），在此之上讨论**数据管道、HTTP 服务、Agent 工具调用**三条线如何收口成一个最小可行故事。

---

## 要解决什么问题（需求叙述）

1. **数据侧**：运行产物散落在不同路径与命名习惯下，需要**增量 ingest、校验 schema、落库（或列式存储）**，并保留到原始文件的**可追溯引用**（URI / 相对路径 / 内容哈希），而不是把大文件拷进数据库。
2. **服务侧**：内部看板、CI 与外部脚本需要**稳定、版本化的只读 API**（分页列表、按标签过滤、单条 run 详情、指标时间线占位），避免每人直接连生产库或翻共享盘。
3. **智能侧**：研究员常提**比较型、检索型**问题（例如「最近三次带 `onnx-exported` 的 run 里，tokens/s 最高的是哪次？config 路径是什么？」）。希望在**严格工具边界**内试验一个 **Agent**：只通过注册好的工具访问 catalog，不任意执行 shell。

非目标（当前阶段明确不做）：

- 不做通用 MLOps 平台，不替代 Weights & Biases / MLflow 的全量能力。
- 不在首版接入真实生产身份体系；仅预留 API Key / 内网假设。
- 不承诺多租户隔离的完整安全模型（课题结题前以**威胁建模文档**形式记录即可）。

---

## 三条技术线如何落在同一主题上

| 方向 | 在 Runstream 里的落点 |
|------|------------------------|
| **数据管道** | Ingest 适配器（文件监听 / 定时扫描）→ Pydantic 校验 → 规范化 `RunRecord` → 写入 SQLite/DuckDB + 可选导出 Parquet |
| **服务化** | FastAPI：`GET /runs`、`GET /runs/{id}`、`GET /health`；后续 `POST /runs`（受控写入）与 OpenAPI 契约 |
| **Agent** | 同一 catalog 上的**只读工具**（`search_runs`、`get_run`、`compare_metrics`），由轻量编排层（如 LangGraph / 自写 ReAct 循环）驱动；**禁止**开放任意代码执行工具 |

---

## 路线图（计划）

### Phase 0 — 契约与样例（当前仓库状态）

- [x] 约定最小 **`meta.json` 形态**（见 `fixtures/example_run/meta.json`）
- [x] 明确非目标与威胁边界（见上文）
- [ ] 补充 JSON Schema（`schemas/run_record.json`）供管道与 API 共用

### Phase 1 — 数据管道 MVP

- [ ] 实现 `runstream ingest once <path>`：扫描目录，解析 `meta.json`，写入本地 SQLite
- [ ] 重复 ingest **幂等**（以 `run_id` 或内容哈希去重）
- [ ] 单元测试：损坏 JSON、缺字段、指标类型漂移

### Phase 2 — 服务化 MVP

- [ ] FastAPI 应用：`/health`、`/runs`、`/runs/{run_id}`
- [ ] 分页与简单过滤（`tag`、`project`、`since`）
- [ ] `Dockerfile` + `docker compose`（api + 卷挂载 catalog）

### Phase 3 — Agent MVP

- [ ] 定义 3～4 个 **OpenAI tool schema** 对齐 Phase 2 API（或直连同一查询层）
- [ ] CLI：`runstream ask "……"` 调用兼容 OpenAI 的 endpoint（环境变量配置 base URL / model）
- [ ] 评测集：10～20 条固定问题 + 期望引用的 `run_id`（回归 Agent 是否胡编）

### Phase 4 — 硬化与扩展（可选）

- [ ] 异步 ingest（队列占位）、只读副本、速率限制
- [ ] 与对象存储预签名 URL 的集成设计（仅文档 + mock）
- [ ] 与现有训练仓库的 **webhook** 对接草案

---

## 仓库结构（规划）

```text
runstream/
  README.md                 # 本文件：背景 + 路线图
  pyproject.toml
  fixtures/example_run/     # 示例运行元数据
  src/runstream/            # 代码入口（随 Phase 1+ 填充）
  schemas/                  # JSON Schema（Phase 0）
  tests/                    # Phase 1 起
```

---

## 本地开发（占位）

```bash
cd runstream
python -m venv .venv
# Windows: .\.venv\Scripts\activate
pip install -e .
```

实现推进到 Phase 1 后，将在此处补充具体命令与配置项。

---

## 协议

研究与原型代码默认 **MIT**（正式开源前可替换为课题组要求的开源协议）。
