# 小店记 MVP 设计规格

## 1. 目标

“小店记”第一版面向五金日杂、建材零售等传统个体商户，完成两条可稳定演示的核心闭环：

1. 店主通过文字或语音描述一笔报价、交易或收款，系统生成结构化候选记录；用户确认、修改后确认或取消后，系统保存完整操作痕迹。
2. 店主用自然语言查询客户欠款、历史报价、当日流水、逾期账目、待确认或异常记录，系统返回结论、明细及原始凭证。

核心演示必须端到端完成：

> 店主说一笔赊账 → AI识别成两项商品 → 一个低置信度字段被高亮 → 店主修改并确认 → 查询“王老板还欠多少钱” → 返回余额、交易明细和原始语音 → 首页出现逾期提醒。

## 2. MVP边界

### 2.1 必须实现

- 文字智能记账、语音记账和结构化手动表单。
- 结构化确认卡片、字段置信度展示和低置信度高亮。
- 直接确认、修改后确认、取消三态留痕。
- 客户主档和客户别名匹配。
- 多商品报价、多商品交易和客户维度收款。
- 参数化自然语言查询：
  - 客户当前欠款；
  - 客户历史报价；
  - 当日交易和收款流水；
  - 逾期未结账目；
  - 待确认记录；
  - 异常记录。
- 查询明细和原始语音或图片凭证追溯。
- 基础逾期提醒。
- Docker Compose一键启动。
- 固定评测样本、评测运行器和可展示的指标结果。
- AI服务失败时，结构化手动表单仍能完成记账。

### 2.2 明确延后

- 通用NL2SQL；仅保留关闭状态的实验入口，不参与任何金额结论。
- 手写账本批量识别。
- 转账截图自动匹配。
- 多智能体自主协同；第一版使用受控工作流服务。
- pgvector。
- 复杂付款核销、退款、退货和历史冲账。
- 微信订阅消息。
- 完整核账智能体。
- 多门店、复杂角色权限、在线支付、税务和会计功能。

## 3. 运行假设

- 第一版服务一个演示商户，所有业务表保留 `shop_id`，但不开发登录和多租户管理界面。
- 金额使用人民币，数据库保存定点十进制值，不使用浮点数。
- 默认时区为 `Asia/Shanghai`。
- 欠款口径为“客户已确认的赊账交易总额减去客户已确认的收款总额”。
- 第一版收款只匹配客户，不进行一笔收款到多笔交易的复杂核销。
- H5是第一交付目标；前端保持uni-app微信小程序编译兼容，但正式发布和审核不属于本地验收条件。

## 4. 总体架构

项目放在现有工作区的独立目录 `xiaodianji/`，并使用独立Git仓库：

```text
xiaodianji/
├── frontend/                   # uni-app + Vue 3 + TypeScript
├── backend/                    # FastAPI应用
├── evaluation/                 # 脱敏固定样本和预期结果
├── deployment/                 # Nginx及部署配置
├── docs/                       # 设计、计划和使用文档
└── docker-compose.yml
```

运行组件：

- `frontend`：移动端H5，提供录音、手动输入、确认、查询和凭证查看。
- `backend`：FastAPI，负责业务接口、AI工作流、确认事务和查询模板。
- `postgres`：保存结构化业务数据、确认记录、提醒和评测结果。
- `minio`：保存原始语音、图片及其他凭证。
- `nginx`：统一提供前端资源和后端反向代理。

MVP不引入Redis、向量数据库和独立任务队列。请求幂等依靠数据库唯一键、确认状态机和请求ID实现。

## 5. 后端模块边界

后端采用按业务能力拆分的模块结构：

- `records`：接收文字、语音或结构化表单，生成候选记录。
- `confirmations`：管理待确认记录、字段修改、三态事件和正式写入事务。
- `customers`：客户主档、别名和候选匹配。
- `ledger`：报价、交易、收款及客户余额计算。
- `queries`：意图分类、实体解析和参数化查询模板。
- `evidences`：文件元数据、对象存储和受控访问。
- `reminders`：逾期规则计算和提醒列表。
- `evaluation`：固定样本运行、字段比较和指标汇总。
- `providers`：ASR和LLM提供方适配器。

模块通过明确的服务接口和Pydantic Schema通信。所谓“记录智能体、查询智能体、核账智能体、提醒智能体”在MVP中均实现为受控服务，不允许自主访问任意工具或数据库。

## 6. 数据模型

### 6.1 商户与客户

- `shops`
  - `id`、`name`、`timezone`、`created_at`
- `customers`
  - `id`、`shop_id`、`name`、`phone`、`notes`、`created_at`
- `customer_aliases`
  - `id`、`shop_id`、`customer_id`、`alias`、`normalized_alias`

同一商户内的标准化别名必须唯一。模糊匹配只产生候选和置信度；存在歧义时必须由用户确认，不能静默合并客户。

### 6.2 报价、交易与收款

- `quotes`
  - `id`、`shop_id`、`customer_id`、`quoted_at`、`total_amount`、`source_evidence_id`
- `quote_items`
  - `id`、`quote_id`、`product`、`spec`、`quantity`、`unit`、`unit_price`、`subtotal`
- `transactions`
  - `id`、`shop_id`、`customer_id`、`occurred_at`、`payment_status`、`total_amount`、`source_evidence_id`
- `transaction_items`
  - `id`、`transaction_id`、`product`、`spec`、`quantity`、`unit`、`unit_price`、`subtotal`
- `payments`
  - `id`、`shop_id`、`customer_id`、`amount`、`paid_at`、`source_evidence_id`

商品小计和总金额由后端使用十进制数重新计算。AI提供的合计只作为候选值和异常校验依据。

### 6.3 凭证与确认

- `evidences`
  - `id`、`shop_id`、`type`、`object_key`、`mime_type`、`size_bytes`、`asr_text`、`created_at`
- `pending_confirmations`
  - `id`、`shop_id`、`target_type`、`source_evidence_id`
  - `extracted_json`、`edited_json`、`field_confidences`
  - `status`、`idempotency_key`、`schema_version`
  - `model_name`、`created_at`、`resolved_at`
- `confirmation_events`
  - `id`、`confirmation_id`、`event_type`、`before_json`、`after_json`、`created_at`

确认状态为：

- `pending`
- `confirmed`
- `confirmed_after_edit`
- `cancelled`

正式报价、交易或收款只能由确认服务创建。记录工作流只能创建 `pending_confirmations`。

### 6.4 提醒、异常与评测

- `reminders`
  - `id`、`shop_id`、`customer_id`、`type`、`due_at`、`status`、`payload`
- `anomalies`
  - `id`、`shop_id`、`type`、`severity`、`status`、`payload`
- `evaluation_cases`
  - `id`、`input_type`、`input_payload`、`expected_json`、`tags`
- `evaluation_runs`
  - `id`、`model_name`、`started_at`、`finished_at`、`summary_json`
- `evaluation_results`
  - `id`、`run_id`、`case_id`、`predicted_json`、`field_scores`、`latency_ms`

## 7. 记账数据流

### 7.1 文字或语音记账

1. 前端生成请求ID。
2. 语音文件先上传为凭证；文字输入创建文本凭证。
3. 语音调用ASR适配器，转写结果保存到凭证。
4. 记录服务调用LLM结构化抽取，输出固定Schema。
5. 后端校验字段类型、金额关系和业务枚举。
6. 客户服务进行标准名、别名和模糊候选匹配。
7. 所有候选字段及置信度写入待确认表。
8. 前端渲染确认卡片，低于阈值的字段高亮。
9. 用户直接确认、修改后确认或取消。
10. 确认服务在单个数据库事务中写正式表、明细和确认事件。
11. 事务成功后刷新客户欠款和逾期提醒查询结果。

默认低置信度阈值为 `0.75`，通过环境配置调整。

### 7.2 手动降级

当ASR、LLM或网络不可用时，前端显示结构化表单。用户填写的内容直接生成候选确认单，不经过AI，但仍经过相同的校验、确认和正式写入事务。

## 8. 查询数据流

1. 查询服务识别查询类型、客户、日期范围和必要参数。
2. 客户名称通过标准名和别名匹配。
3. 查询类型映射到固定的参数化查询服务。
4. 后端计算金额和口径，不由LLM计算。
5. LLM可对已计算结果生成简短自然语言描述，但不得修改金额。
6. 接口返回：
   - 查询结论；
   - 计算口径；
   - 结构化明细；
   - 关联凭证链接；
   - 无匹配或歧义提示。

任何无法识别的查询返回支持的查询示例，不进入通用NL2SQL。

## 9. API边界

主要接口：

- `POST /api/v1/evidences`
- `POST /api/v1/records/text`
- `POST /api/v1/records/voice`
- `POST /api/v1/records/manual`
- `GET /api/v1/confirmations`
- `GET /api/v1/confirmations/{id}`
- `PATCH /api/v1/confirmations/{id}`
- `POST /api/v1/confirmations/{id}/confirm`
- `POST /api/v1/confirmations/{id}/cancel`
- `GET /api/v1/customers`
- `GET /api/v1/customers/{id}`
- `GET /api/v1/ledger/transactions/{id}`
- `GET /api/v1/ledger/quotes/{id}`
- `POST /api/v1/queries`
- `GET /api/v1/reminders`
- `POST /api/v1/evaluations/run`
- `GET /api/v1/evaluations/{id}`
- `GET /api/v1/health`

修改确认单只更新 `edited_json`，不得写正式账目。确认和取消接口要求幂等键。

## 10. 前端设计

页面包括：

- 首页：说一笔、文字记账、手动表单、快捷查账和逾期提醒。
- 录音页：录音状态、时长、上传和失败降级。
- 文字记账页。
- 结构化手动表单页。
- 确认卡片页：字段编辑、低置信度高亮、三态操作。
- 查询页：类聊天输入、结论、明细和凭证入口。
- 客户列表和客户详情页。
- 报价、交易、收款明细页。
- 凭证查看页。
- 待确认、提醒和异常列表页。
- 评测结果页。

适老化要求：

- 首页主要入口在一屏内完成。
- 默认字号不低于移动端常用正文的大字号档。
- 关键金额和主要操作具有高对比度。
- 重要操作使用文字标签，不只依赖图标。
- 确认与取消在颜色、位置和文案上明确区分。

## 11. AI提供方设计

ASR和LLM均通过接口适配器调用：

- 真实提供方适配器：由环境变量配置地址、模型和密钥。
- 测试适配器：根据固定样本返回确定结果。
- 失败适配器：用于验证降级流程。

结构化抽取必须使用JSON Schema或等价的结构化输出能力，并由Pydantic再次校验。模型不得直接执行SQL、写数据库或计算最终余额。

密钥只通过环境变量或密钥文件注入，不进入Git、日志或前端包。

## 12. 错误处理和可靠性

- 文件上传限制类型、大小和时长。
- 对象上传成功但业务处理失败时保留凭证并标记失败状态，允许重试。
- 同一请求ID不得创建重复候选记录。
- 同一确认单不得生成两笔正式记录。
- 确认事务失败时不得留下部分明细或错误余额。
- 第三方AI超时返回可理解的错误，并展示手动录入入口。
- 查询金额全部来自后端确定性计算。
- 凭证访问使用后端授权或短时签名地址，不公开对象存储管理接口。
- 日志不得记录API密钥、完整音频内容或不必要的客户隐私数据。

## 13. 测试与评测

### 13.1 自动化测试

- 后端单元测试：
  - 金额与日期规范化；
  - 多商品总额计算；
  - 客户别名和歧义匹配；
  - 确认状态机；
  - 查询模板；
  - 逾期规则；
  - 指标计算。
- 后端集成测试：
  - PostgreSQL事务；
  - 幂等确认；
  - MinIO凭证关联；
  - AI失败降级。
- 前端测试：
  - 确认卡片编辑；
  - 低置信度高亮；
  - 三态操作；
  - 查询结果和凭证入口。
- 端到端测试：
  - 核心七环节演示脚本；
  - AI失败后的手动记账；
  - 重复提交不产生重复账目。

### 13.2 固定评测集

评测集覆盖：

- 单商品和多商品；
- 赊账、已付款和收款；
- 客户别名；
- 商品规格；
- 口语化数量、单位和金额；
- 日期省略；
- 低置信度字段；
- 无法匹配和歧义客户；
- AI服务异常。

输出指标：

- 客户识别准确率；
- 商品识别准确率；
- 数量识别准确率；
- 金额识别准确率；
- 付款状态识别准确率；
- 直接确认率；
- 修改后确认率；
- 取消率；
- 平均处理时延。

直接确认率以所有已处理确认单为分母；演示时同时展示样本数量，避免只有百分比没有统计规模。

## 14. Docker与运行

`docker compose up --build` 必须启动前端、后端、PostgreSQL、MinIO和Nginx，并自动执行数据库迁移。项目提供：

- `.env.example`
- 健康检查
- 演示数据初始化命令
- 固定评测运行命令
- 数据卷说明
- 本地启动、停止、备份和恢复说明

没有真实AI密钥时，系统以测试提供方启动，完整UI和演示流程仍可验证；真实语音效果验收必须使用真实ASR配置。

## 15. 验收标准

MVP完成必须同时满足：

1. 核心七环节演示脚本端到端通过，不手工修改数据库。
2. 多商品记录能够正确生成主表、明细和客户欠款。
3. 低置信度字段正确高亮，修改后确认保留前后差异。
4. 直接确认、修改后确认和取消均有可查询事件记录。
5. 查询余额与交易、收款流水计算一致。
6. 查询明细能够打开关联原始语音或图片凭证。
7. 逾期客户在首页提醒中出现。
8. AI服务失败时，手动结构化录入仍可完成记账。
9. 重复上传或重复确认不产生重复正式记录。
10. 固定评测集能够输出规定指标及样本数量。
11. 自动化测试全部通过。
12. Docker Compose能够从干净环境一键启动并完成演示。

## 16. 实施顺序

1. 建立独立仓库、后端基础结构、数据库迁移和测试框架。
2. 先以测试驱动方式完成手动结构化记账、待确认和确认事务。
3. 完成客户别名、多商品报价、交易、收款和余额查询。
4. 接入文字抽取、语音上传、ASR和凭证。
5. 完成参数化查询、明细和凭证追溯。
6. 完成逾期提醒和异常展示。
7. 完成uni-app页面与端到端联调。
8. 完成固定评测和指标页面。
9. 完成Docker Compose、演示数据和部署验证。
10. 按核心脚本验收并集中打磨移动端体验。
