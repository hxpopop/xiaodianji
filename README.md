# 小店记 MVP

面向传统个体商户的多模态 AI 报价与往来账助手。AI 结果只进入待确认区；用户确认后，独立确认接口才写入正式账本。

## 一键启动

要求：Docker Desktop 与 Docker Compose。

```powershell
Copy-Item .env.example .env
docker compose up --build -d
Invoke-RestMethod http://localhost:8080/api/v1/health
```

打开 `http://localhost:8080`。如需标准 80 端口，可在 `.env` 修改 `XDJ_HTTP_PORT`。停止服务使用 `docker compose down`；需要同时清空演示数据时使用 `docker compose down -v`。

## 演示数据与评测

```powershell
docker compose exec backend python -m xiaodianji.demo.seed
.\scripts\run-evaluation.ps1 -ApiBase http://localhost:8080/api/v1
```

演示商户 ID 固定为 `00000000-0000-0000-0000-000000000101`。种子可重复运行，不会重复创建客户、报价、交易、收款、凭证或提醒。

核心演示顺序：

1. “说一笔”选择固定演示音频，生成两项商品的待确认记录。
2. 查看低置信度字段，修改后确认。
3. 查询“王老板还欠多少钱”。
4. 展开交易明细并查看原始凭证。
5. 回到首页查看逾期提醒。
6. 在“我的”运行固定评测，展示准确率分子、分母、样本量和时延。

AI 服务失败时，语音页会明确提供“改用手动输入”；手动记账不依赖 ASR 或 LLM。

## 接入真实 AI 服务

默认 `fake` 提供方无需密钥，可完整演示。需要真实服务时，在 `.env` 中配置：

- `XDJ_ASR_PROVIDER`、`XDJ_ASR_URL`、`XDJ_ASR_API_KEY`、`XDJ_ASR_MODEL`
- `XDJ_LLM_PROVIDER`、`XDJ_LLM_URL`、`XDJ_LLM_API_KEY`、`XDJ_LLM_MODEL`

密钥不要提交到 Git；`.env.example` 只有占位符。

## 测试

```powershell
cd backend
python -m pytest -q

cd ..\frontend
npm test
npm run type-check
npm run build:h5
npm run build:mp-weixin
```

## 备份与恢复

```powershell
.\scripts\backup.ps1 -Output .\backup.sql
.\scripts\restore.ps1 -InputFile .\backup.sql
```

## MVP 边界

本版不提供通用 NL2SQL 金额结论、手写账本批量识别、转账截图匹配、复杂核销、微信订阅消息、pgvector 或自主多智能体协同。金额查询优先使用受控模板，AI 服务异常时保留手动记账主流程。
