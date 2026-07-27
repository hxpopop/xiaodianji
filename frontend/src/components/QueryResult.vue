<script setup lang="ts">
import type { QueryResponse } from '../api/types'
import EvidenceLink from './EvidenceLink.vue'

defineProps<{ result: QueryResponse }>()

const emit = defineEmits<{
  (event: 'open-evidence', evidenceId: string): void
}>()

const hiddenKeys = new Set(['id', 'evidence_id'])
const labels: Record<string, string> = {
  type: '类型',
  customer_name: '客户',
  product: '商品',
  quantity: '数量',
  unit: '单位',
  unit_price: '单价',
  subtotal: '小计',
  amount: '金额',
  occurred_at: '交易时间',
  paid_at: '收款时间',
  quoted_at: '报价时间',
  due_at: '到期时间',
  target_type: '记录类型',
  severity: '程度',
  message: '说明',
  created_at: '创建时间',
}

const typeLabels: Record<string, string> = {
  transaction: '交易',
  payment: '收款',
  quote: '报价',
  pending: '待确认',
}

function visibleEntries(detail: Record<string, unknown>) {
  return Object.entries(detail).filter(([key, value]) => (
    !hiddenKeys.has(key) && value !== null && value !== undefined && value !== ''
  ))
}

function labelFor(key: string) {
  return labels[key] || key.replace(/_/g, ' ')
}

function valueFor(key: string, value: unknown) {
  if (key === 'type' || key === 'target_type') {
    return typeLabels[String(value)] || String(value)
  }
  if (key.endsWith('_at')) {
    const date = new Date(String(value))
    return Number.isNaN(date.getTime()) ? String(value) : date.toLocaleString('zh-CN')
  }
  return String(value)
}
</script>

<template>
  <article class="query-result" aria-live="polite">
    <header>
      <p class="eyebrow">查询结论</p>
      <h2>{{ result.answer }}</h2>
      <strong v-if="result.amount !== null" class="amount">¥{{ result.amount }}</strong>
    </header>

    <section v-if="result.calculation_basis" class="basis" aria-labelledby="basis-heading">
      <h3 id="basis-heading">计算口径</h3>
      <p>{{ result.calculation_basis }}</p>
    </section>

    <section class="details" aria-labelledby="details-heading">
      <h3 id="details-heading">结构化明细</h3>
      <p v-if="result.details.length === 0" class="quiet">本次查询没有匹配到明细。</p>
      <dl v-for="(detail, index) in result.details" :key="String(detail.id || index)">
        <template v-for="[key, value] in visibleEntries(detail)" :key="key">
          <dt>{{ labelFor(key) }}</dt>
          <dd>{{ valueFor(key, value) }}</dd>
        </template>
      </dl>
    </section>

    <section v-if="result.ambiguity?.candidates?.length" class="ambiguity">
      <h3>需要确认客户</h3>
      <p>
        {{ result.ambiguity.candidates.map(candidate => candidate.name).join('、') }}
      </p>
    </section>

    <section v-if="result.evidence_ids.length" class="evidence-actions" aria-label="关联凭证">
      <EvidenceLink
        v-for="(evidenceId, index) in result.evidence_ids"
        :key="evidenceId"
        :evidence-id="evidenceId"
        :label="result.evidence_ids.length > 1 ? `查看凭证 ${index + 1}` : '查看凭证'"
        @open="emit('open-evidence', $event)"
      />
    </section>
  </article>
</template>

<style scoped lang="scss">
@use '../styles/tokens.scss' as *;

.query-result {
  margin-top: $space-4;
  border-top: 1px solid $ink;
}

header,
.basis,
.details,
.ambiguity {
  padding: $space-3 0;
  border-bottom: 1px solid $line;
}

.eyebrow,
h2,
h3,
p,
dl,
dt,
dd {
  margin: 0;
}

.eyebrow,
.quiet,
dt {
  color: $muted;
}

h2 {
  margin-top: .25rem;
  font-size: 1.375rem;
  line-height: 1.35;
}

h3 {
  margin-bottom: $space-1;
  font-size: 1rem;
}

.amount {
  display: block;
  margin-top: $space-2;
  font-size: $amount-text;
  letter-spacing: -.03em;
}

dl {
  display: grid;
  grid-template-columns: minmax(5rem, .7fr) minmax(0, 1.3fr);
  gap: .35rem $space-2;
  padding: $space-2 0;
}

dl + dl {
  border-top: 1px solid $line;
}

dd {
  overflow-wrap: anywhere;
}

.evidence-actions {
  display: flex;
  flex-wrap: wrap;
  gap: $space-2;
  padding-top: $space-3;
}
</style>
