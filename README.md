# ContentPilot

ContentPilot 是一个面向中文内容发布前质检与改写的本地应用。它把规则检索、风险识别、平台化改写、多轮协作和历史记忆组合成一个三栏工作台，适合处理小红书、公众号、知乎、短视频等平台的文案。

## 主要功能

- 发布前风险质检：识别绝对化承诺、健康功效承诺、强诱导、焦虑营销等高风险表达。
- 双版本改写：只输出「稳妥合规版」和「转化增强版」，降低用户选择成本。
- 改写强度控制：轻度优化、中度改写、深度重写。
- 表达力度控制：克制自然、适度营销、强吸引但合规。
- 无限次继续修改：基于当前选中的版本继续调整，而不是每轮从原文重来。
- 聊天历史窗口：保留原文、系统分析、用户修改意见和每轮输出摘要。
- 历史管理：支持删除当前会话、删除单条历史、清空全部历史。
- 知识库管理：维护平台规则、风险表达、案例和自定义知识，并支持重建向量索引。
- 评测报告：使用固定样本集验证风险识别、改写成功率和流程稳定性。

## 技术栈

- Python 3.12
- FastAPI
- Streamlit
- LangGraph
- SQLite
- BM25 + Chroma 向量检索
- DashScope/OpenAI-compatible LLM 与 Embedding 接口，可回退到本地 hash embedding

## 项目结构

```text
application/          Agent 工作流、节点和应用服务
config/               配置读取
domain/               Pydantic 请求与响应模型
infrastructure/       数据库、检索、LLM、工具函数
interfaces/http/      FastAPI 路由
frontend/             Streamlit 前台和知识库后台
prompts/              可管理的提示词模板
data/                 规则、风险表达、案例和种子历史
eval/                 评测用例与评测报告生成器
scripts/              初始化、知识库扩展、向量索引重建脚本
tests/                自动化测试
```

## 环境准备

推荐使用 Python 3.12 环境。

```powershell
conda activate py312
pip install -r requirements.txt
```

复制环境变量模板并按需填写：

```powershell
Copy-Item .env.example .env
```

常用配置项：

```env
LLM_PROVIDER=mock
ENABLE_LLM_OPTIMIZE=false
LLM_API_KEY=
LLM_MODEL=qwen-plus
LLM_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions

EMBEDDING_PROVIDER=hash
EMBEDDING_API_KEY=
EMBEDDING_MODEL=text-embedding-v3
EMBEDDING_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1/embeddings
```

本地开发建议先使用 `LLM_PROVIDER=mock`、`EMBEDDING_PROVIDER=hash`。如果启用 DashScope，请确认网络和 API Key 可用。

## 初始化与索引

初始化 SQLite 表：

```powershell
python scripts/init_db.py
```

重建 Chroma 向量索引：

```powershell
python scripts/rebuild_vector_store.py
```

如需清空旧索引后重建：

```powershell
python scripts/rebuild_vector_store.py --clear
```

如果 Windows 提示 `WinError 32`，说明有后端、前端、VSCode Python 终端或 Chroma 会话正在占用 `data/chroma` 文件。关闭相关进程后重试。

## 启动服务

启动后端 API：

```powershell
python -m uvicorn interfaces.http.main:app --reload --port 8000
```

启动前台工作台：

```powershell
python -m streamlit run frontend/streamlit_app.py --server.port 8501
```

启动知识库后台：

```powershell
python -m streamlit run frontend/admin_app.py --server.port 8502
```

访问地址：

- API 文档：http://127.0.0.1:8000/docs
- 前台工作台：http://127.0.0.1:8501
- 知识库后台：http://127.0.0.1:8502

## 常用 API

- `GET /health`：基础健康检查
- `GET /api/v1/health/diagnostics`：完整诊断
- `POST /api/v1/content/analyze`：单平台质检与改写
- `POST /api/v1/content/batch`：多平台批量生成
- `POST /api/v1/content/refine`：基于当前版本继续修改
- `GET /api/v1/history/tasks`：历史任务列表
- `DELETE /api/v1/history/tasks/{task_id}`：删除单条历史
- `DELETE /api/v1/history/tasks?user_id=default_user`：清空指定用户历史
- `GET /api/v1/history/conversations/{conversation_id}/messages`：读取会话消息
- `POST /api/v1/knowledge/items`：新增知识库条目
- `POST /api/v1/knowledge/reindex`：重建知识库索引

## 测试与评测

运行自动化测试：

```powershell
python -m pytest
```

运行静态检查：

```powershell
python -m ruff check .
```

运行评测报告：

```powershell
python eval/run_eval_report.py
```

评测输出会生成到 `eval/reports/`，该目录属于运行产物，不建议提交到版本库。

## 数据与隐私

- `contentpilot.db` 保存本地历史任务、版本、反馈、偏好和会话消息。
- `data/chroma/` 保存本地向量索引，可通过脚本重建。
- `.env` 可能包含 API Key，禁止提交。
- 前端提供删除当前会话、删除单条历史、清空全部历史，便于处理敏感文案和商业内容。

## 开发注意事项

- 运行前确认没有旧的 Uvicorn、Streamlit 或 Python 进程占用 `8000`、`8501`、`8502`。
- 如果 Chroma 索引文件被占用，先关闭相关进程，再运行 `python scripts/rebuild_vector_store.py --clear`。
- 当前默认保留数据库和向量索引作为本地运行状态；清理代码仓库时只删除缓存、日志和评测输出。
