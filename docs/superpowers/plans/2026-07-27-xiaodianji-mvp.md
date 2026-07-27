# 小店记 MVP Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 构建可用Docker Compose一键启动、完整跑通语音赊账到欠款查询和逾期提醒演示链路的“小店记”比赛级MVP。

**Architecture:** 项目采用uni-app移动端H5、FastAPI模块化单体、PostgreSQL和MinIO。所有AI结果先进入待确认区，只有确认服务能在数据库事务中写入报价、交易或收款正式表；金额查询由受控参数化服务确定性计算，ASR和LLM通过可替换适配器接入。

**Tech Stack:** Python 3.12+、FastAPI、Pydantic 2、SQLAlchemy 2、Alembic、PostgreSQL 16、MinIO、pytest、uni-app、Vue 3、TypeScript、Vitest、Playwright、Docker Compose、Nginx。

## Global Constraints

- 项目根目录为 `xiaodianji/`，不得修改父目录中的现有财务文档项目。
- 第一版使用单一演示商户，但所有业务表必须包含 `shop_id`。
- 金额使用Python `Decimal`和PostgreSQL `NUMERIC(18, 2)`，不得使用浮点数。
- 默认时区固定为 `Asia/Shanghai`。
- AI工作流只能写入 `pending_confirmations`，正式账目只能由确认服务创建。
- 欠款口径固定为“客户已确认赊账交易总额减客户已确认收款总额”。
- 低置信度默认阈值为 `0.75`，由环境变量配置。
- 通用NL2SQL保持禁用，不参与金额结论。
- AI服务不可用时，结构化手动表单仍须完成记账。
- 每个实现任务必须遵循先失败测试、最小实现、通过测试、提交的顺序。

---

## File Map

### Backend

- `backend/pyproject.toml`：Python依赖、pytest和静态检查配置。
- `backend/src/xiaodianji/main.py`：FastAPI应用工厂和路由注册。
- `backend/src/xiaodianji/config.py`：环境配置。
- `backend/src/xiaodianji/db.py`：异步数据库引擎、Session和事务边界。
- `backend/src/xiaodianji/models/`：SQLAlchemy模型，按商户客户、账目、确认、凭证、提醒和评测拆分。
- `backend/src/xiaodianji/schemas/`：Pydantic输入输出契约。
- `backend/src/xiaodianji/customers/`：客户别名归一化和匹配。
- `backend/src/xiaodianji/confirmations/`：确认状态机、修改留痕和正式写入。
- `backend/src/xiaodianji/ledger/`：报价、交易、收款和余额。
- `backend/src/xiaodianji/evidences/`：对象存储接口和凭证服务。
- `backend/src/xiaodianji/providers/`：ASR、LLM真实和测试适配器。
- `backend/src/xiaodianji/records/`：文字、语音和手动记录工作流。
- `backend/src/xiaodianji/queries/`：意图识别和参数化查询。
- `backend/src/xiaodianji/reminders/`：逾期提醒。
- `backend/src/xiaodianji/evaluation/`：固定样本和指标运行器。
- `backend/alembic/`：数据库迁移。
- `backend/tests/`：单元和集成测试。

### Frontend

- `frontend/src/pages/index/`：首页和逾期提醒摘要。
- `frontend/src/pages/record-text/`：文字记账。
- `frontend/src/pages/record-voice/`：录音、上传和降级。
- `frontend/src/pages/record-manual/`：结构化手动表单。
- `frontend/src/pages/confirmation/`：确认卡片和字段编辑。
- `frontend/src/pages/query/`：参数化自然语言查账。
- `frontend/src/pages/customers/`：客户列表。
- `frontend/src/pages/customer-detail/`：客户余额、报价、交易和收款。
- `frontend/src/pages/evidence/`：凭证查看。
- `frontend/src/pages/reminders/`：待确认、提醒和异常。
- `frontend/src/pages/evaluation/`：指标展示。
- `frontend/src/api/`：类型安全API客户端。
- `frontend/src/stores/`：Pinia状态。
- `frontend/src/components/`：确认卡片、商品明细和状态组件。
- `frontend/tests/`：Vitest组件测试。
- `frontend/e2e/`：Playwright核心演示测试。

### Deployment and Evaluation

- `evaluation/cases.jsonl`：脱敏固定评测样本。
- `deployment/nginx.conf`：静态资源和API反向代理。
- `docker-compose.yml`：前端、后端、PostgreSQL、MinIO和Nginx。
- `.env.example`：无密钥默认配置和测试提供方配置。
- `README.md`：启动、演示、评测、备份和恢复说明。

---

### Task 1: 后端基础与健康检查

**Files:**
- Create: `backend/pyproject.toml`
- Create: `backend/src/xiaodianji/__init__.py`
- Create: `backend/src/xiaodianji/config.py`
- Create: `backend/src/xiaodianji/main.py`
- Create: `backend/tests/conftest.py`
- Create: `backend/tests/test_health.py`
- Create: `.gitignore`

**Interfaces:**
- Produces: `create_app() -> FastAPI`
- Produces: `Settings`，包含 `app_env`、`database_url`、`object_storage_*`、`confidence_threshold`、`timezone`

- [ ] **Step 1: 写健康检查失败测试**

```python
from fastapi.testclient import TestClient
from xiaodianji.main import create_app


def test_health_returns_service_status():
    client = TestClient(create_app())
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "xiaodianji"}
```

- [ ] **Step 2: 运行单测并确认因应用不存在而失败**

Run: `cd backend && python -m pytest tests/test_health.py -v`

Expected: FAIL，提示无法导入 `xiaodianji.main`。

- [ ] **Step 3: 创建最小应用工厂和配置**

```python
# backend/src/xiaodianji/main.py
from fastapi import FastAPI


def create_app() -> FastAPI:
    app = FastAPI(title="小店记 API", version="0.1.0")

    @app.get("/api/v1/health")
    async def health() -> dict[str, str]:
        return {"status": "ok", "service": "xiaodianji"}

    return app


app = create_app()
```

`config.py` 使用 `pydantic-settings`，默认置信度 `Decimal("0.75")`、时区 `Asia/Shanghai`，测试环境不得要求真实密钥。

- [ ] **Step 4: 配置测试和忽略文件**

`pyproject.toml` 声明FastAPI、Pydantic 2、pydantic-settings、SQLAlchemy 2、Alembic、psycopg、httpx、pytest和pytest-asyncio，并把 `src` 加入pytest导入路径。

`.gitignore` 必须忽略 `.env`、`.venv/`、`node_modules/`、构建输出、缓存、测试报告、上传文件和数据库卷，不忽略 `.env.example`。

- [ ] **Step 5: 运行测试**

Run: `cd backend && python -m pytest tests/test_health.py -v`

Expected: PASS。

- [ ] **Step 6: 提交**

```bash
git add .gitignore backend
git commit -m "chore: bootstrap FastAPI service"
```

---

### Task 2: PostgreSQL模型和初始迁移

**Files:**
- Create: `backend/src/xiaodianji/db.py`
- Create: `backend/src/xiaodianji/models/base.py`
- Create: `backend/src/xiaodianji/models/shop.py`
- Create: `backend/src/xiaodianji/models/customer.py`
- Create: `backend/src/xiaodianji/models/ledger.py`
- Create: `backend/src/xiaodianji/models/confirmation.py`
- Create: `backend/src/xiaodianji/models/evidence.py`
- Create: `backend/src/xiaodianji/models/reminder.py`
- Create: `backend/src/xiaodianji/models/evaluation.py`
- Create: `backend/src/xiaodianji/models/__init__.py`
- Create: `backend/alembic.ini`
- Create: `backend/alembic/env.py`
- Create: `backend/alembic/versions/0001_initial_schema.py`
- Create: `backend/tests/test_models.py`

**Interfaces:**
- Produces: `Base`, `async_session_factory`, `get_session()`
- Produces: SQLAlchemy模型 `Shop`, `Customer`, `CustomerAlias`, `Quote`, `QuoteItem`, `Transaction`, `TransactionItem`, `Payment`, `Evidence`, `PendingConfirmation`, `ConfirmationEvent`, `Reminder`, `Anomaly`, `EvaluationCase`, `EvaluationRun`, `EvaluationResult`

- [ ] **Step 1: 写模型约束失败测试**

```python
def test_money_columns_are_fixed_precision():
    assert str(Transaction.__table__.c.total_amount.type) == "NUMERIC(18, 2)"
    assert str(Payment.__table__.c.amount.type) == "NUMERIC(18, 2)"


def test_customer_alias_is_unique_per_shop():
    constraint_names = {
        c.name for c in CustomerAlias.__table__.constraints if c.name is not None
    }
    assert "uq_customer_alias_shop_normalized" in constraint_names


def test_confirmation_idempotency_is_unique_per_shop():
    constraint_names = {
        c.name for c in PendingConfirmation.__table__.constraints if c.name is not None
    }
    assert "uq_confirmation_shop_idempotency" in constraint_names
```

- [ ] **Step 2: 运行模型测试并确认失败**

Run: `cd backend && python -m pytest tests/test_models.py -v`

Expected: FAIL，模型尚未定义。

- [ ] **Step 3: 实现基础模型和枚举**

所有ID使用UUID。金额列统一为 `Numeric(18, 2)`。JSON候选数据使用PostgreSQL `JSONB`。确认状态枚举严格为：

```python
class ConfirmationStatus(StrEnum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    CONFIRMED_AFTER_EDIT = "confirmed_after_edit"
    CANCELLED = "cancelled"
```

交易付款状态严格为 `unpaid`、`paid`，MVP不引入部分付款状态；部分收款通过客户维度余额体现。

- [ ] **Step 4: 编写初始Alembic迁移**

迁移创建全部业务表、外键和以下索引：

- 客户标准名和别名；
- 报价、交易、收款的 `shop_id + customer_id + 日期`；
- 待确认的 `shop_id + status + created_at`；
- 提醒的 `shop_id + status + due_at`；
- `shop_id + idempotency_key` 唯一约束。

- [ ] **Step 5: 运行模型测试和迁移往返测试**

Run: `cd backend && python -m pytest tests/test_models.py -v`

Run: `cd backend && alembic upgrade head`

Expected: 测试PASS，迁移成功。

- [ ] **Step 6: 提交**

```bash
git add backend/src/xiaodianji/db.py backend/src/xiaodianji/models backend/alembic.ini backend/alembic backend/tests/test_models.py
git commit -m "feat: add core ledger database schema"
```

---

### Task 3: 客户别名归一化和歧义匹配

**Files:**
- Create: `backend/src/xiaodianji/customers/normalization.py`
- Create: `backend/src/xiaodianji/customers/service.py`
- Create: `backend/src/xiaodianji/schemas/customer.py`
- Create: `backend/src/xiaodianji/api/customers.py`
- Create: `backend/tests/customers/test_matching.py`
- Create: `backend/tests/customers/test_api.py`

**Interfaces:**
- Produces: `normalize_customer_name(value: str) -> str`
- Produces: `CustomerMatch(customer_id: UUID | None, candidates: list[CustomerCandidate], confidence: Decimal, requires_confirmation: bool)`
- Produces: `CustomerService.match(shop_id: UUID, spoken_name: str) -> CustomerMatch`

- [ ] **Step 1: 写归一化和歧义匹配失败测试**

```python
def test_normalize_customer_name_removes_title_and_spaces():
    assert normalize_customer_name(" 王 老板 ") == "王"


async def test_ambiguous_alias_requires_confirmation(customer_service, seeded_customers):
    result = await customer_service.match(seeded_customers.shop_id, "老王")
    assert result.customer_id is None
    assert result.requires_confirmation is True
    assert len(result.candidates) == 2
```

- [ ] **Step 2: 运行测试并确认失败**

Run: `cd backend && python -m pytest tests/customers -v`

Expected: FAIL，匹配服务尚不存在。

- [ ] **Step 3: 实现确定性匹配顺序**

匹配顺序固定为：

1. 标准名精确匹配；
2. 别名精确匹配；
3. 标准化名称精确匹配；
4. `rapidfuzz` 相似度候选。

唯一精确结果置信度为 `1.00`；唯一高相似结果可返回候选但低于阈值时仍要求确认；多个相近结果不得自动选择。

- [ ] **Step 4: 实现客户查询接口**

提供：

- `GET /api/v1/customers`
- `GET /api/v1/customers/{id}`

客户详情返回当前欠款、最近交易、最近报价和别名列表，余额值由后续账目服务注入。

- [ ] **Step 5: 运行客户测试**

Run: `cd backend && python -m pytest tests/customers -v`

Expected: PASS。

- [ ] **Step 6: 提交**

```bash
git add backend/src/xiaodianji/customers backend/src/xiaodianji/schemas/customer.py backend/src/xiaodianji/api/customers.py backend/tests/customers
git commit -m "feat: add customer alias matching"
```

---

### Task 4: 手动候选记录和确认状态机

**Files:**
- Create: `backend/src/xiaodianji/schemas/record.py`
- Create: `backend/src/xiaodianji/schemas/confirmation.py`
- Create: `backend/src/xiaodianji/records/manual.py`
- Create: `backend/src/xiaodianji/confirmations/service.py`
- Create: `backend/src/xiaodianji/api/records.py`
- Create: `backend/src/xiaodianji/api/confirmations.py`
- Create: `backend/tests/confirmations/test_state_machine.py`
- Create: `backend/tests/confirmations/test_manual_record.py`

**Interfaces:**
- Produces: `Money = Annotated[Decimal, Field(ge=0, decimal_places=2)]`
- Produces: `RecordDraft`, `QuoteDraft`, `TransactionDraft`, `PaymentDraft`, `LineItemDraft`, `FieldConfidence`
- Produces: `ConfirmationService.update_draft()`, `confirm()`, `cancel()`
- Consumes: `CustomerService.match()`

- [ ] **Step 1: 写金额和多商品Schema失败测试**

```python
def test_transaction_draft_recalculates_total():
    draft = TransactionDraft.model_validate({
        "customer_name": "王老板",
        "occurred_at": "2026-07-27T10:00:00+08:00",
        "payment_status": "unpaid",
        "items": [
            {"product": "插座", "quantity": "10", "unit": "个", "unit_price": "12.00"},
            {"product": "电线", "quantity": "2", "unit": "卷", "unit_price": "150.00"}
        ]
    })
    assert draft.total_amount == Decimal("420.00")
```

- [ ] **Step 2: 写三态和幂等失败测试**

```python
async def test_edited_confirmation_records_before_and_after(confirmation_service, pending_draft):
    await confirmation_service.update_draft(
        pending_draft.id,
        {"items.0.quantity": "10"},
    )
    result = await confirmation_service.confirm(
        pending_draft.id,
        idempotency_key="confirm-001",
    )
    assert result.status == ConfirmationStatus.CONFIRMED_AFTER_EDIT
    assert result.events[-1].before_json != result.events[-1].after_json


async def test_duplicate_confirmation_returns_same_formal_record(confirmation_service, pending_draft):
    first = await confirmation_service.confirm(pending_draft.id, "confirm-002")
    second = await confirmation_service.confirm(pending_draft.id, "confirm-002")
    assert second.formal_record_id == first.formal_record_id
```

- [ ] **Step 3: 运行确认测试并确认失败**

Run: `cd backend && python -m pytest tests/confirmations -v`

Expected: FAIL。

- [ ] **Step 4: 实现手动候选创建**

`POST /api/v1/records/manual` 接收严格结构化Schema，写入 `pending_confirmations`，字段置信度全部设为 `1.00`，相同 `shop_id + idempotency_key` 返回已存在候选。

- [ ] **Step 5: 实现确认状态机**

允许转换：

```text
pending -> confirmed
pending -> confirmed_after_edit
pending -> cancelled
```

任何终态不能再次修改；相同幂等键重复确认返回第一次结果，不同幂等键重复确认返回HTTP 409。

- [ ] **Step 6: 运行确认测试**

Run: `cd backend && python -m pytest tests/confirmations -v`

Expected: PASS。

- [ ] **Step 7: 提交**

```bash
git add backend/src/xiaodianji/schemas backend/src/xiaodianji/records backend/src/xiaodianji/confirmations backend/src/xiaodianji/api backend/tests/confirmations
git commit -m "feat: add confirmation-first recording workflow"
```

---

### Task 5: 确认事务、正式账目和客户欠款

**Files:**
- Create: `backend/src/xiaodianji/ledger/service.py`
- Create: `backend/src/xiaodianji/ledger/balance.py`
- Create: `backend/src/xiaodianji/schemas/ledger.py`
- Create: `backend/src/xiaodianji/api/ledger.py`
- Modify: `backend/src/xiaodianji/confirmations/service.py`
- Create: `backend/tests/ledger/test_confirmation_transaction.py`
- Create: `backend/tests/ledger/test_balance.py`

**Interfaces:**
- Produces: `LedgerService.create_from_confirmation(session, draft) -> FormalRecordRef`
- Produces: `BalanceService.customer_balance(shop_id, customer_id) -> Decimal`
- Consumes: validated `RecordDraft`

- [ ] **Step 1: 写确认写账和回滚失败测试**

```python
async def test_confirm_creates_transaction_and_two_items(
    confirmation_service, transaction_draft
):
    result = await confirmation_service.confirm(transaction_draft.id, "write-001")
    transaction = await load_transaction(result.formal_record_id)
    assert len(transaction.items) == 2
    assert transaction.total_amount == Decimal("420.00")


async def test_item_failure_rolls_back_parent_transaction(
    confirmation_service, invalid_transaction_draft
):
    with pytest.raises(DomainValidationError):
        await confirmation_service.confirm(invalid_transaction_draft.id, "write-002")
    assert await count_transactions() == 0
```

- [ ] **Step 2: 写客户余额失败测试**

```python
async def test_balance_is_unpaid_transactions_minus_payments(balance_service, ledger_seed):
    balance = await balance_service.customer_balance(
        ledger_seed.shop_id, ledger_seed.customer_id
    )
    assert balance == Decimal("220.00")
```

- [ ] **Step 3: 运行账目测试并确认失败**

Run: `cd backend && python -m pytest tests/ledger -v`

Expected: FAIL。

- [ ] **Step 4: 实现单事务正式写入**

确认服务在一个 `session.begin()` 中：

1. 使用行锁读取待确认单；
2. 验证仍为 `pending`；
3. 重新解析Pydantic Schema；
4. 重新计算小计和总额；
5. 创建客户或绑定已确认客户；
6. 创建正式主表和全部明细；
7. 写确认事件和正式记录ID；
8. 更新确认终态。

- [ ] **Step 5: 实现确定性余额和明细接口**

提供：

- `GET /api/v1/ledger/transactions/{id}`
- `GET /api/v1/ledger/quotes/{id}`
- `GET /api/v1/customers/{id}/balance`

接口返回金额字符串，例如 `"420.00"`，避免JSON浮点误差。

- [ ] **Step 6: 运行账目测试**

Run: `cd backend && python -m pytest tests/ledger -v`

Expected: PASS。

- [ ] **Step 7: 提交**

```bash
git add backend/src/xiaodianji/ledger backend/src/xiaodianji/schemas/ledger.py backend/src/xiaodianji/api/ledger.py backend/src/xiaodianji/confirmations/service.py backend/tests/ledger
git commit -m "feat: write confirmed ledger records atomically"
```

---

### Task 6: 凭证存储和受控访问

**Files:**
- Create: `backend/src/xiaodianji/evidences/storage.py`
- Create: `backend/src/xiaodianji/evidences/service.py`
- Create: `backend/src/xiaodianji/schemas/evidence.py`
- Create: `backend/src/xiaodianji/api/evidences.py`
- Create: `backend/tests/evidences/test_upload.py`
- Create: `backend/tests/evidences/test_access.py`

**Interfaces:**
- Produces: `ObjectStorage.put()`, `get_presigned_url()`, `delete()`
- Produces: `EvidenceService.create_upload() -> EvidenceRead`
- Produces: `EvidenceService.attach_transcript(evidence_id, transcript)`

- [ ] **Step 1: 写上传限制失败测试**

```python
def test_rejects_unsupported_evidence_type(client):
    response = client.post(
        "/api/v1/evidences",
        files={"file": ("payload.exe", b"bad", "application/octet-stream")},
    )
    assert response.status_code == 415


def test_accepts_audio_and_returns_evidence_id(client, fake_storage):
    response = client.post(
        "/api/v1/evidences",
        files={"file": ("trade.wav", b"RIFF-data", "audio/wav")},
    )
    assert response.status_code == 201
    assert response.json()["type"] == "audio"
```

- [ ] **Step 2: 运行凭证测试并确认失败**

Run: `cd backend && python -m pytest tests/evidences -v`

Expected: FAIL。

- [ ] **Step 3: 实现对象存储协议和MinIO适配器**

允许的MIME类型限定为常见音频和 `image/jpeg`、`image/png`。对象键使用 `shop_id/yyyy/mm/uuid.ext`，禁止使用用户文件名作为对象键。

- [ ] **Step 4: 实现凭证链接**

详情接口只返回短时签名URL，默认有效期300秒。数据库保存对象键而不是公开URL。

- [ ] **Step 5: 运行凭证测试**

Run: `cd backend && python -m pytest tests/evidences -v`

Expected: PASS。

- [ ] **Step 6: 提交**

```bash
git add backend/src/xiaodianji/evidences backend/src/xiaodianji/schemas/evidence.py backend/src/xiaodianji/api/evidences.py backend/tests/evidences
git commit -m "feat: add traceable evidence storage"
```

---

### Task 7: LLM、ASR适配器和智能候选记录

**Files:**
- Create: `backend/src/xiaodianji/providers/base.py`
- Create: `backend/src/xiaodianji/providers/fake.py`
- Create: `backend/src/xiaodianji/providers/openai_compatible.py`
- Create: `backend/src/xiaodianji/providers/http_asr.py`
- Create: `backend/src/xiaodianji/providers/factory.py`
- Create: `backend/src/xiaodianji/records/extraction.py`
- Create: `backend/src/xiaodianji/records/text.py`
- Create: `backend/src/xiaodianji/records/voice.py`
- Modify: `backend/src/xiaodianji/api/records.py`
- Create: `backend/tests/providers/test_fake_provider.py`
- Create: `backend/tests/records/test_text_record.py`
- Create: `backend/tests/records/test_voice_record.py`
- Create: `backend/tests/records/test_fallback.py`

**Interfaces:**
- Produces: `ASRProvider.transcribe(audio: bytes, mime_type: str) -> ASRResult`
- Produces: `ExtractionProvider.extract(text: str) -> ExtractionResult`
- Produces: `RecordWorkflow.from_text()` 和 `from_voice()`
- Consumes: `EvidenceService`, `CustomerService`, `RecordDraft`

- [ ] **Step 1: 写固定双商品抽取失败测试**

```python
async def test_text_record_creates_two_item_pending_confirmation(client):
    response = client.post(
        "/api/v1/records/text",
        headers={"Idempotency-Key": "text-001"},
        json={"text": "王老板拿十个插座每个十二块，两卷电线每卷一百五，先欠着"},
    )
    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "pending"
    assert len(body["draft"]["items"]) == 2
    assert body["draft"]["total_amount"] == "420.00"
```

- [ ] **Step 2: 写低置信度和AI失败测试**

```python
async def test_low_confidence_quantity_is_preserved_for_highlight(client):
    body = (await post_demo_voice(client)).json()
    assert body["field_confidences"]["items.1.quantity"] == "0.62"


async def test_provider_failure_returns_manual_fallback(client, failing_provider):
    response = client.post(
        "/api/v1/records/text",
        headers={"Idempotency-Key": "text-fail-001"},
        json={"text": "王老板拿了一批插座"},
    )
    assert response.status_code == 503
    assert response.json()["fallback"] == "manual_form"
```

- [ ] **Step 3: 运行记录测试并确认失败**

Run: `cd backend && python -m pytest tests/providers tests/records -v`

Expected: FAIL。

- [ ] **Step 4: 实现提供方协议和测试提供方**

测试提供方对固定演示语句返回两项商品，其中 `items.1.quantity` 置信度为 `0.62`。测试输出仍必须经过生产Pydantic Schema校验。

- [ ] **Step 5: 实现OpenAI兼容结构化抽取**

提示词只负责候选抽取，输出必须符合 `RecordDraft` JSON Schema。后端覆盖模型总额、重新计算金额、限制业务枚举并保存模型名和Schema版本。

- [ ] **Step 6: 实现HTTP ASR适配器**

ASR地址、密钥、模型和超时由环境变量提供。ASR失败不得创建不完整正式账目；已上传凭证保留失败状态，允许用户进入手动表单。

- [ ] **Step 7: 运行记录测试**

Run: `cd backend && python -m pytest tests/providers tests/records -v`

Expected: PASS。

- [ ] **Step 8: 提交**

```bash
git add backend/src/xiaodianji/providers backend/src/xiaodianji/records backend/src/xiaodianji/api/records.py backend/tests/providers backend/tests/records
git commit -m "feat: add text and voice extraction workflows"
```

---

### Task 8: 参数化自然语言查询

**Files:**
- Create: `backend/src/xiaodianji/queries/intents.py`
- Create: `backend/src/xiaodianji/queries/parser.py`
- Create: `backend/src/xiaodianji/queries/service.py`
- Create: `backend/src/xiaodianji/schemas/query.py`
- Create: `backend/src/xiaodianji/api/queries.py`
- Create: `backend/tests/queries/test_intents.py`
- Create: `backend/tests/queries/test_service.py`

**Interfaces:**
- Produces: `QueryIntent`，取值为 `customer_balance`、`historical_quote`、`daily_flow`、`overdue`、`pending`、`anomaly`
- Produces: `QueryRequest(question: str)`
- Produces: `QueryResponse(answer, calculation_basis, details, evidence_ids, ambiguity)`

- [ ] **Step 1: 写支持意图失败测试**

```python
@pytest.mark.parametrize(
    ("question", "intent"),
    [
        ("王老板还欠多少钱", QueryIntent.CUSTOMER_BALANCE),
        ("上次给王老板报的插座多少钱", QueryIntent.HISTORICAL_QUOTE),
        ("今天一共卖了多少", QueryIntent.DAILY_FLOW),
        ("哪些账逾期了", QueryIntent.OVERDUE),
        ("有哪些待确认", QueryIntent.PENDING),
        ("最近有哪些异常", QueryIntent.ANOMALY),
    ],
)
def test_supported_query_intents(question, intent):
    assert parse_intent(question).intent is intent
```

- [ ] **Step 2: 写余额查询明细失败测试**

```python
async def test_balance_query_returns_basis_details_and_evidence(client, ledger_seed):
    response = client.post("/api/v1/queries", json={"question": "王老板还欠多少钱"})
    body = response.json()
    assert body["amount"] == "220.00"
    assert body["calculation_basis"] == "赊账交易总额 - 收款总额"
    assert len(body["details"]) >= 2
    assert body["details"][0]["evidence_id"] is not None
```

- [ ] **Step 3: 运行查询测试并确认失败**

Run: `cd backend && python -m pytest tests/queries -v`

Expected: FAIL。

- [ ] **Step 4: 实现规则优先解析**

先用明确关键词和日期解析识别意图，再使用结构化LLM分类作为可选兜底。分类结果只能选择六个枚举，不得生成SQL。

- [ ] **Step 5: 实现六个参数化查询**

所有数据库调用通过SQLAlchemy参数绑定。金额由后端聚合；自然语言答案只格式化已计算值。无法匹配客户时返回候选列表，存在歧义时不返回金额结论。

- [ ] **Step 6: 运行查询测试**

Run: `cd backend && python -m pytest tests/queries -v`

Expected: PASS。

- [ ] **Step 7: 提交**

```bash
git add backend/src/xiaodianji/queries backend/src/xiaodianji/schemas/query.py backend/src/xiaodianji/api/queries.py backend/tests/queries
git commit -m "feat: add deterministic natural language queries"
```

---

### Task 9: 逾期提醒和基础异常

**Files:**
- Create: `backend/src/xiaodianji/reminders/service.py`
- Create: `backend/src/xiaodianji/reminders/rules.py`
- Create: `backend/src/xiaodianji/schemas/reminder.py`
- Create: `backend/src/xiaodianji/api/reminders.py`
- Create: `backend/tests/reminders/test_overdue.py`
- Create: `backend/tests/reminders/test_anomalies.py`

**Interfaces:**
- Produces: `ReminderService.refresh(shop_id, as_of) -> ReminderSummary`
- Produces: `GET /api/v1/reminders`

- [ ] **Step 1: 写逾期规则失败测试**

```python
async def test_unpaid_transaction_becomes_overdue_after_configured_days(
    reminder_service, old_unpaid_transaction
):
    summary = await reminder_service.refresh(
        old_unpaid_transaction.shop_id,
        as_of=date(2026, 7, 27),
    )
    assert summary.overdue_count == 1
    assert summary.items[0].customer_name == "王老板"
```

- [ ] **Step 2: 写金额异常失败测试**

```python
def test_amount_mismatch_creates_anomaly():
    result = validate_amounts(
        item_subtotals=[Decimal("120.00"), Decimal("300.00")],
        stated_total=Decimal("400.00"),
    )
    assert result.type == "amount_mismatch"
```

- [ ] **Step 3: 运行提醒测试并确认失败**

Run: `cd backend && python -m pytest tests/reminders -v`

Expected: FAIL。

- [ ] **Step 4: 实现逾期和异常规则**

默认逾期天数为30天，可配置。已结清客户不显示逾期提醒。基础异常只包括金额不一致和重复幂等请求，不实现自动核销和客户聚类。

- [ ] **Step 5: 运行提醒测试**

Run: `cd backend && python -m pytest tests/reminders -v`

Expected: PASS。

- [ ] **Step 6: 提交**

```bash
git add backend/src/xiaodianji/reminders backend/src/xiaodianji/schemas/reminder.py backend/src/xiaodianji/api/reminders.py backend/tests/reminders
git commit -m "feat: add overdue reminders and basic anomalies"
```

---

### Task 10: 固定评测集和指标

**Files:**
- Create: `evaluation/cases.jsonl`
- Create: `backend/src/xiaodianji/evaluation/metrics.py`
- Create: `backend/src/xiaodianji/evaluation/runner.py`
- Create: `backend/src/xiaodianji/schemas/evaluation.py`
- Create: `backend/src/xiaodianji/api/evaluation.py`
- Create: `backend/tests/evaluation/test_metrics.py`
- Create: `backend/tests/evaluation/test_runner.py`

**Interfaces:**
- Produces: `score_case(expected, predicted) -> FieldScores`
- Produces: `EvaluationRunner.run(case_path) -> EvaluationSummary`
- Produces: `POST /api/v1/evaluations/run`
- Produces: `GET /api/v1/evaluations/{id}`

- [ ] **Step 1: 写核心字段指标失败测试**

```python
def test_metrics_count_each_core_field_and_sample_size():
    summary = aggregate_scores([
        FieldScores(
            customer=True,
            products=[True, False],
            quantities=[True, True],
            amounts=[True, True],
            payment_status=True,
        )
    ])
    assert summary.customer_accuracy == Decimal("1.0000")
    assert summary.product_accuracy == Decimal("0.5000")
    assert summary.case_count == 1
```

- [ ] **Step 2: 写三态确认指标失败测试**

```python
def test_confirmation_rates_use_resolved_confirmations_as_denominator():
    rates = confirmation_rates(
        direct=6,
        edited=3,
        cancelled=1,
    )
    assert rates.direct_rate == Decimal("0.6000")
    assert rates.edited_rate == Decimal("0.3000")
    assert rates.cancelled_rate == Decimal("0.1000")
```

- [ ] **Step 3: 运行评测测试并确认失败**

Run: `cd backend && python -m pytest tests/evaluation -v`

Expected: FAIL。

- [ ] **Step 4: 创建脱敏固定样本**

`cases.jsonl` 至少包含20条样本，覆盖单商品、多商品、赊账、已付款、收款、别名、规格、日期省略、低置信度、歧义客户和提供方失败。每条包含稳定ID、输入、预期结构和标签。

- [ ] **Step 5: 实现运行器和指标接口**

评测运行保存模型名、每条预测、字段分数、时延和汇总。API返回准确率时同时返回分子、分母和样本数量。

- [ ] **Step 6: 运行评测测试**

Run: `cd backend && python -m pytest tests/evaluation -v`

Expected: PASS。

- [ ] **Step 7: 提交**

```bash
git add evaluation backend/src/xiaodianji/evaluation backend/src/xiaodianji/schemas/evaluation.py backend/src/xiaodianji/api/evaluation.py backend/tests/evaluation
git commit -m "feat: add reproducible extraction evaluation"
```

---

### Task 11: uni-app基础、首页和确认卡片

**Files:**
- Create: `frontend/package.json`
- Create: `frontend/tsconfig.json`
- Create: `frontend/vite.config.ts`
- Create: `frontend/src/main.ts`
- Create: `frontend/src/App.vue`
- Create: `frontend/src/pages.json`
- Create: `frontend/src/styles/tokens.scss`
- Create: `frontend/src/api/client.ts`
- Create: `frontend/src/api/types.ts`
- Create: `frontend/src/stores/record.ts`
- Create: `frontend/src/pages/index/index.vue`
- Create: `frontend/src/pages/record-text/index.vue`
- Create: `frontend/src/pages/record-manual/index.vue`
- Create: `frontend/src/pages/confirmation/index.vue`
- Create: `frontend/src/components/ConfirmationCard.vue`
- Create: `frontend/src/components/LineItemEditor.vue`
- Create: `frontend/tests/ConfirmationCard.test.ts`

**Interfaces:**
- Produces: `apiClient` 方法与后端 `/api/v1` 契约一致。
- Produces: `RecordStore.createTextDraft()`, `createManualDraft()`, `updateDraft()`, `confirmDraft()`, `cancelDraft()`
- Consumes: 后端确认、记录和提醒接口。

- [ ] **Step 1: 写低置信度高亮失败测试**

```typescript
it('highlights a field below the confidence threshold', () => {
  const wrapper = mount(ConfirmationCard, {
    props: {
      draft: demoDraft,
      fieldConfidences: { 'items.1.quantity': '0.62' },
      confidenceThreshold: '0.75'
    }
  })
  expect(wrapper.get('[data-field="items.1.quantity"]').classes()).toContain('is-low-confidence')
})
```

- [ ] **Step 2: 写修改后确认事件失败测试**

```typescript
it('submits edited draft before confirmation', async () => {
  const wrapper = mount(ConfirmationCard, { props: confirmationProps })
  await wrapper.get('[data-field="items.0.quantity"] input').setValue('10')
  await wrapper.get('[data-action="confirm"]').trigger('click')
  expect(wrapper.emitted('confirm')?.[0]?.[0]).toMatchObject({ edited: true })
})
```

- [ ] **Step 3: 运行组件测试并确认失败**

Run: `cd frontend && npm run test -- ConfirmationCard.test.ts`

Expected: FAIL。

- [ ] **Step 4: 实现设计Token和适老化首页**

正文、金额、按钮字号和点击区域集中定义。首页在常见手机视口一屏内显示“说一笔、文字记账、手动输入、查欠款”和逾期摘要。

- [ ] **Step 5: 实现手动表单和确认卡片**

确认卡片必须显示客户、日期、付款状态、商品数组、数量、单位、单价、小计、合计和凭证。确认、取消使用明确文字；编辑后调用PATCH，再调用确认接口。

- [ ] **Step 6: 运行组件测试和类型检查**

Run: `cd frontend && npm run test`

Run: `cd frontend && npm run type-check`

Expected: 全部PASS。

- [ ] **Step 7: 提交**

```bash
git add frontend
git commit -m "feat: add accessible recording and confirmation UI"
```

---

### Task 12: 语音、查询、客户、提醒和评测页面

**Files:**
- Create: `frontend/src/pages/record-voice/index.vue`
- Create: `frontend/src/pages/query/index.vue`
- Create: `frontend/src/pages/customers/index.vue`
- Create: `frontend/src/pages/customer-detail/index.vue`
- Create: `frontend/src/pages/evidence/index.vue`
- Create: `frontend/src/pages/reminders/index.vue`
- Create: `frontend/src/pages/evaluation/index.vue`
- Create: `frontend/src/components/QueryResult.vue`
- Create: `frontend/src/components/EvidenceLink.vue`
- Create: `frontend/src/components/ReminderCard.vue`
- Create: `frontend/tests/QueryResult.test.ts`
- Create: `frontend/tests/VoiceFallback.test.ts`

**Interfaces:**
- Produces: 语音上传后跳转确认页。
- Produces: 查询结果的结论、口径、明细和凭证链接。
- Consumes: 后端凭证、语音记录、查询、客户、提醒和评测接口。

- [ ] **Step 1: 写查询凭证展示失败测试**

```typescript
it('renders amount, calculation basis, details and evidence action', () => {
  const wrapper = mount(QueryResult, { props: { result: demoBalanceResult } })
  expect(wrapper.text()).toContain('220.00')
  expect(wrapper.text()).toContain('赊账交易总额 - 收款总额')
  expect(wrapper.get('[data-action="open-evidence"]').exists()).toBe(true)
})
```

- [ ] **Step 2: 写语音失败降级测试**

```typescript
it('shows manual form action when ASR fails', async () => {
  mockRecordVoice.mockRejectedValue({ fallback: 'manual_form' })
  const wrapper = mount(VoiceRecordPage)
  await wrapper.vm.submitRecordedAudio(demoBlob)
  expect(wrapper.get('[data-action="manual-fallback"]').isVisible()).toBe(true)
})
```

- [ ] **Step 3: 运行页面测试并确认失败**

Run: `cd frontend && npm run test -- QueryResult.test.ts VoiceFallback.test.ts`

Expected: FAIL。

- [ ] **Step 4: 实现录音和上传**

使用uni-app录音能力封装开始、暂停、结束、时长和权限状态。H5不支持或权限被拒绝时明确显示文字和结构化手动入口。

- [ ] **Step 5: 实现查询、客户和凭证页面**

查询页提供六类示例问题；详情必须展示后端口径和结构化明细。凭证页通过短时链接播放音频或显示图片。

- [ ] **Step 6: 实现提醒和评测页面**

提醒页面展示逾期天数、客户、余额和查看明细操作。评测页面展示准确率、分子、分母、样本量和平均时延。

- [ ] **Step 7: 运行前端全部检查**

Run: `cd frontend && npm run test`

Run: `cd frontend && npm run type-check`

Expected: 全部PASS。

- [ ] **Step 8: 提交**

```bash
git add frontend
git commit -m "feat: complete query voice and evaluation UI"
```

---

### Task 13: 核心演示端到端测试和种子数据

**Files:**
- Create: `backend/src/xiaodianji/demo/seed.py`
- Create: `backend/tests/demo/test_seed.py`
- Create: `frontend/playwright.config.ts`
- Create: `frontend/e2e/core-demo.spec.ts`
- Create: `frontend/e2e/ai-failure.spec.ts`
- Create: `scripts/seed-demo.ps1`
- Create: `scripts/run-evaluation.ps1`

**Interfaces:**
- Produces: `python -m xiaodianji.demo.seed`
- Produces: Playwright核心演示和降级脚本。

- [ ] **Step 1: 写核心七环节E2E测试**

```typescript
test('voice debt record becomes traceable balance and overdue reminder', async ({ page }) => {
  await page.goto('/')
  await page.getByText('说一笔').click()
  await page.setInputFiles('[data-testid="demo-audio"]', 'e2e/fixtures/two-items.wav')
  await page.getByText('开始识别').click()
  await expect(page.locator('[data-field="items.1.quantity"]')).toHaveClass(/is-low-confidence/)
  await page.locator('[data-field="items.1.quantity"] input').fill('2')
  await page.getByText('修改后确认').click()
  await page.getByPlaceholder('问问今天的账').fill('王老板还欠多少钱')
  await page.getByText('查询').click()
  await expect(page.getByText('420.00')).toBeVisible()
  await page.getByText('查看原始语音').click()
  await expect(page.locator('audio')).toBeVisible()
  await page.goto('/')
  await expect(page.getByText('逾期提醒')).toBeVisible()
})
```

- [ ] **Step 2: 写AI失败手动记账E2E测试**

测试将后端提供方切换到失败模式，确认页面出现结构化表单入口，填写并确认后能够在客户余额中查到记录。

- [ ] **Step 3: 实现幂等种子数据**

种子脚本创建演示商户、王老板客户、别名、历史报价、逾期交易、收款和凭证元数据。重复运行不得生成重复数据。

- [ ] **Step 4: 运行后端演示测试**

Run: `cd backend && python -m pytest tests/demo -v`

Expected: PASS。

- [ ] **Step 5: 运行E2E测试**

Run: `cd frontend && npm run e2e`

Expected: 两个场景PASS。

- [ ] **Step 6: 提交**

```bash
git add backend/src/xiaodianji/demo backend/tests/demo frontend/e2e frontend/playwright.config.ts scripts
git commit -m "test: cover the complete MVP demonstration"
```

---

### Task 14: Docker Compose、Nginx和交付文档

**Files:**
- Create: `backend/Dockerfile`
- Create: `frontend/Dockerfile`
- Create: `deployment/nginx.conf`
- Create: `docker-compose.yml`
- Create: `.env.example`
- Create: `README.md`
- Create: `scripts/backup.ps1`
- Create: `scripts/restore.ps1`
- Create: `backend/tests/test_deployment_contract.py`

**Interfaces:**
- Produces: `docker compose up --build`
- Produces: `http://localhost` 前端和 `/api/v1/health` 后端。

- [ ] **Step 1: 写部署契约失败测试**

```python
def test_compose_declares_required_services(compose_document):
    assert set(compose_document["services"]) >= {
        "frontend", "backend", "postgres", "minio", "nginx"
    }


def test_example_environment_contains_no_real_secret(env_example):
    assert "CHANGE_ME" in env_example
    assert "sk-" not in env_example
```

- [ ] **Step 2: 运行部署测试并确认失败**

Run: `cd backend && python -m pytest tests/test_deployment_contract.py -v`

Expected: FAIL。

- [ ] **Step 3: 实现容器和健康检查**

Compose要求：

- PostgreSQL和MinIO使用命名卷；
- 后端启动前执行 `alembic upgrade head`；
- 后端等待PostgreSQL健康；
- Nginx统一代理 `/api/`；
- 测试提供方为无密钥默认模式；
- 真实提供方通过 `.env` 切换；
- 不把任何密钥写入镜像。

- [ ] **Step 4: 编写README和运维脚本**

README包含：

- 环境要求；
- 一键启动和停止；
- 测试提供方演示；
- 真实ASR和LLM配置字段；
- 演示数据初始化；
- 固定评测运行；
- 数据备份和恢复；
- 核心演示脚本；
- 已知MVP边界。

- [ ] **Step 5: 运行全部测试**

Run: `cd backend && python -m pytest -q`

Run: `cd frontend && npm run test`

Run: `cd frontend && npm run type-check`

Expected: 全部PASS。

- [ ] **Step 6: 验证干净容器启动**

Run: `docker compose config`

Run: `docker compose up --build -d`

Run: `Invoke-RestMethod http://localhost/api/v1/health`

Expected: 返回 `{"status":"ok","service":"xiaodianji"}`。

- [ ] **Step 7: 运行核心演示和评测**

Run: `.\scripts\seed-demo.ps1`

Run: `.\scripts\run-evaluation.ps1`

Run: `cd frontend && npm run e2e`

Expected: 核心演示PASS，评测输出客户、商品、数量、金额、付款状态和确认率指标及样本数量。

- [ ] **Step 8: 提交**

```bash
git add backend/Dockerfile frontend/Dockerfile deployment docker-compose.yml .env.example README.md scripts backend/tests/test_deployment_contract.py
git commit -m "chore: package the MVP for one-command startup"
```

---

## Final Verification

- [ ] 运行 `git status --short`，确认没有意外未提交文件。
- [ ] 运行后端全部测试并保存通过摘要。
- [ ] 运行前端组件测试和类型检查并保存通过摘要。
- [ ] 从空数据卷启动Docker Compose。
- [ ] 执行演示种子、固定评测和两个Playwright场景。
- [ ] 手工检查常见手机视口：首页一屏、字号、对比度、按钮点击区域和低置信度高亮。
- [ ] 检查日志不包含API密钥、完整音频内容或不必要的客户隐私数据。
- [ ] 检查通用NL2SQL入口保持禁用。
- [ ] 核对设计规格中的12项验收标准均有测试或演示证据。
- [ ] 创建最终交付提交：

```bash
git add .
git commit -m "release: complete xiaodianji MVP"
```
