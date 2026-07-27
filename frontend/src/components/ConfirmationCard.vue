<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import type {
  ConfirmationRead,
  EvidenceRead,
  PaymentStatus,
  QuoteDraft,
  RecordDraft,
  TransactionDraft,
} from '../api/types'
import LineItemEditor from './LineItemEditor.vue'

type ItemRecordDraft = QuoteDraft | TransactionDraft
type EvidenceState = 'loading' | 'ready' | 'missing' | 'unavailable'
type LineItemConfidenceField = 'product' | 'spec' | 'quantity' | 'unit' | 'unit_price' | 'subtotal'

const props = withDefaults(defineProps<{
  confirmation: ConfirmationRead
  confidenceThreshold?: number
  evidence?: EvidenceRead | null
  evidenceState?: EvidenceState
}>(), {
  confidenceThreshold: 0.75,
  evidence: null,
  evidenceState: undefined,
})
const emit = defineEmits<{
  (event: 'confirm', payload: { draft: RecordDraft; edited: boolean }): void
  (event: 'cancel'): void
}>()

const clone = <T>(value: T): T => JSON.parse(JSON.stringify(value)) as T
const draft = ref<RecordDraft>(clone(props.confirmation.effective_json))
const baseline = ref(JSON.stringify(props.confirmation.effective_json))
const validationErrors = ref<string[]>([])

watch(
  () => props.confirmation,
  (value) => {
    draft.value = clone(value.effective_json)
    baseline.value = JSON.stringify(value.effective_json)
    validationErrors.value = []
  },
  { deep: true },
)

const itemDraft = computed<ItemRecordDraft | null>(() => (
  draft.value.target_type === 'payment' ? null : draft.value
))
const dateLabel = computed(() => (
  draft.value.target_type === 'quote'
    ? '报价日期'
    : draft.value.target_type === 'payment'
      ? '收款日期'
      : '交易日期'
))
const datePath = computed(() => (
  draft.value.target_type === 'quote'
    ? 'quoted_at'
    : draft.value.target_type === 'payment'
      ? 'paid_at'
      : 'occurred_at'
))
const dateValue = computed(() => (
  draft.value.target_type === 'quote'
    ? draft.value.quoted_at
    : draft.value.target_type === 'payment'
      ? draft.value.paid_at
      : draft.value.occurred_at
))
const dateInputValue = computed(() => {
  const date = new Date(dateValue.value)
  if (Number.isNaN(date.getTime())) return dateValue.value.slice(0, 16)
  const local = new Date(date.getTime() - date.getTimezoneOffset() * 60_000)
  return local.toISOString().slice(0, 16)
})
const total = computed(() => (
  draft.value.target_type === 'payment' ? draft.value.amount : draft.value.total_amount
))
const totalPath = computed(() => (
  draft.value.target_type === 'payment' ? 'amount' : 'total_amount'
))
const formattedTotal = computed(() => (
  Number.isFinite(Number(total.value)) ? Number(total.value).toFixed(2) : '—'
))
const evidenceId = computed(() => draft.value.source_evidence_id)
const resolvedEvidenceState = computed<EvidenceState>(() => (
  props.evidenceState ?? (evidenceId.value ? 'unavailable' : 'missing')
))
const evidenceTypeLabel = computed(() => {
  if (props.evidence?.type === 'audio') return '语音凭证'
  if (props.evidence?.type === 'image') return '图片凭证'
  if (props.evidence?.type === 'text') return '文字凭证'
  return '原始凭证'
})
const evidenceActionLabel = computed(() => {
  if (props.evidence?.type === 'audio') return '播放原始音频'
  if (props.evidence?.type === 'image') return '查看原始图片'
  return '查看原始文本'
})

function confidenceBelow(path: string) {
  const raw = props.confirmation.field_confidences[path]
  if (raw === undefined) return false
  const confidence = Number(raw)
  return Number.isFinite(confidence) && confidence < props.confidenceThreshold
}

function lineItemConfidence(index: number): Partial<Record<LineItemConfidenceField, boolean>> {
  return {
    product: confidenceBelow(`items.${index}.product`),
    spec: confidenceBelow(`items.${index}.spec`),
    quantity: confidenceBelow(`items.${index}.quantity`),
    unit: confidenceBelow(`items.${index}.unit`),
    unit_price: confidenceBelow(`items.${index}.unit_price`),
    subtotal: confidenceBelow(`items.${index}.subtotal`),
  }
}

function updateCustomer(customerName: string) {
  draft.value = { ...draft.value, customer_name: customerName }
}

function updateDate(value: string) {
  const parsed = new Date(value)
  const normalized = Number.isNaN(parsed.getTime()) ? value : parsed.toISOString()
  const current = draft.value
  if (current.target_type === 'quote') {
    draft.value = { ...current, quoted_at: normalized }
  } else if (current.target_type === 'payment') {
    draft.value = { ...current, paid_at: normalized }
  } else {
    draft.value = { ...current, occurred_at: normalized }
  }
}

function updatePaymentStatus(paymentStatus: PaymentStatus) {
  const current = draft.value
  if (current.target_type === 'transaction') {
    draft.value = { ...current, payment_status: paymentStatus }
  }
}

function updateItem(index: number, item: TransactionDraft['items'][number]) {
  const current = draft.value
  if (current.target_type === 'payment') return
  const items = [...current.items]
  const subtotal = item.quantity * item.unit_price
  items[index] = {
    ...item,
    subtotal: Number.isFinite(subtotal) ? Number(subtotal.toFixed(2)) : Number.NaN,
  }
  const calculatedTotal = items.reduce((sum, line) => sum + line.subtotal, 0)
  draft.value = {
    ...current,
    items,
    total_amount: Number.isFinite(calculatedTotal)
      ? Number(calculatedTotal.toFixed(2))
      : Number.NaN,
  }
  validationErrors.value = []
}

function validateDraft() {
  const errors: string[] = []
  if (itemDraft.value) {
    itemDraft.value.items.forEach((item, index) => {
      if (!Number.isFinite(item.quantity) || item.quantity <= 0) {
        errors.push(`第 ${index + 1} 项数量必须大于 0。`)
      }
      if (!Number.isFinite(item.unit_price) || item.unit_price < 0) {
        errors.push(`第 ${index + 1} 项单价不能小于 0。`)
      }
    })
  }
  validationErrors.value = errors
  return errors.length === 0
}

function submit() {
  if (!validateDraft()) return
  emit('confirm', {
    draft: draft.value,
    edited: JSON.stringify(draft.value) !== baseline.value,
  })
}
</script>

<template>
  <article class="confirmation-card" aria-labelledby="confirmation-heading">
    <header>
      <p class="eyebrow">请核对后再记账</p>
      <h1 id="confirmation-heading">确认这笔记录</h1>
    </header>

    <section class="summary" aria-label="记录摘要">
      <label
        data-field="customer_name"
        :class="{ 'is-low-confidence': confidenceBelow('customer_name') }"
      >
        <span class="field-label">客户</span>
        <input
          :value="draft.customer_name"
          @input="updateCustomer(($event.target as HTMLInputElement).value)"
        />
        <span v-if="confidenceBelow('customer_name')" class="confidence-note">
          客户识别把握较低，请核对客户
        </span>
      </label>

      <label
        :data-field="datePath"
        :class="{ 'is-low-confidence': confidenceBelow(datePath) }"
      >
        <span class="field-label">{{ dateLabel }}</span>
        <input
          type="datetime-local"
          :value="dateInputValue"
          @input="updateDate(($event.target as HTMLInputElement).value)"
        />
        <span v-if="confidenceBelow(datePath)" class="confidence-note">
          日期识别把握较低，请核对日期
        </span>
      </label>

      <label
        v-if="draft.target_type === 'transaction'"
        data-field="payment_status"
        :class="{ 'is-low-confidence': confidenceBelow('payment_status') }"
      >
        <span class="field-label">付款状态</span>
        <select
          :value="draft.payment_status"
          @change="updatePaymentStatus(($event.target as HTMLSelectElement).value as PaymentStatus)"
        >
          <option value="unpaid">赊账未收</option>
          <option value="paid">已收款</option>
        </select>
        <span v-if="confidenceBelow('payment_status')" class="confidence-note">
          付款状态识别把握较低，请核对付款状态
        </span>
      </label>
    </section>

    <section v-if="itemDraft" aria-labelledby="items-heading">
      <h2 id="items-heading">商品明细</h2>
      <LineItemEditor
        v-for="(item, index) in itemDraft.items"
        :key="index"
        :item="item"
        :index="index"
        :low-confidence-fields="lineItemConfidence(index)"
        @update:item="updateItem(index, $event)"
      />
    </section>

    <section
      class="total"
      :data-field="totalPath"
      :class="{ 'is-low-confidence': confidenceBelow(totalPath) }"
    >
      <span>合计</span>
      <strong>¥{{ formattedTotal }}</strong>
      <span v-if="confidenceBelow(totalPath)" class="confidence-note">
        合计识别把握较低，请核对合计
      </span>
    </section>

    <section class="evidence" aria-label="原始凭证">
      <h2>原始凭证</h2>
      <p v-if="resolvedEvidenceState === 'loading'" aria-live="polite">正在加载原始凭证…</p>
      <p v-else-if="resolvedEvidenceState === 'missing'">本次没有关联原始凭证。</p>
      <p v-else-if="resolvedEvidenceState === 'unavailable'">原始凭证暂时无法查看，请稍后重试。</p>
      <div v-else-if="evidence" class="evidence-details">
        <p><strong>凭证类型：</strong>{{ evidenceTypeLabel }}</p>
        <p v-if="evidence.original_filename"><strong>原始文件：</strong>{{ evidence.original_filename }}</p>
        <p v-if="evidence.asr_text"><strong>转写内容：</strong>{{ evidence.asr_text }}</p>
        <div
          v-if="evidence.access_url && evidence.type === 'audio'"
          class="audio-action"
          data-action="open-evidence"
        >
          <span>{{ evidenceActionLabel }}</span>
          <audio :src="evidence.access_url" controls />
        </div>
        <navigator
          v-else-if="evidence.access_url"
          class="evidence-action"
          data-action="open-evidence"
          :url="evidence.access_url"
        >
          {{ evidenceActionLabel }}
        </navigator>
        <p v-else class="evidence-unavailable">原始文件暂时不可播放或查看。</p>
      </div>
      <p v-else>原始凭证暂时无法查看，请稍后重试。</p>
    </section>

    <section v-if="validationErrors.length" class="validation-errors" role="alert">
      <h2>请先修改以下内容</h2>
      <p v-for="message in validationErrors" :key="message">{{ message }}</p>
    </section>

    <footer>
      <button class="confirm" type="button" data-action="confirm" @click="submit">确认记账</button>
      <button class="cancel" type="button" data-action="cancel" @click="emit('cancel')">取消这笔记录</button>
    </footer>
  </article>
</template>

<style scoped lang="scss">
@use '../styles/tokens.scss' as *;

.confirmation-card {
  max-width: 42rem;
  margin: 0 auto;
  padding: $space-4 $space-3 calc($space-5 + env(safe-area-inset-bottom));
  background: $surface;
}

header {
  margin-bottom: $space-4;
}

.eyebrow {
  margin: 0 0 .25rem;
  color: $muted;
  font-size: .9375rem;
}

h1,
h2 {
  letter-spacing: -.02em;
}

h1 {
  margin: 0;
  font-size: 2rem;
  line-height: 1.15;
}

h2 {
  font-size: 1.25rem;
}

.summary {
  display: grid;
  gap: $space-2;
  margin-bottom: $space-4;
}

.summary label {
  display: grid;
  grid-template-columns: minmax(5rem, .7fr) minmax(0, 1.3fr);
  align-items: center;
  gap: $space-1 $space-2;
  padding-bottom: $space-2;
  border-bottom: 1px solid $line;
}

.field-label {
  color: $muted;
}

.summary input,
.summary select {
  width: 100%;
  min-height: $control-height;
  padding: 0 .75rem;
  border: 1px solid $line;
  border-radius: $radius-small;
  background: $surface;
  color: $ink;
  font-weight: 700;
}

.total {
  display: grid;
  grid-template-columns: 1fr auto;
  align-items: baseline;
  margin: $space-4 0;
  padding: $space-3 0;
  border-top: 1px solid $ink;
  border-bottom: 1px solid $ink;
}

.total strong {
  font-size: $amount-text;
  letter-spacing: -.03em;
}

.is-low-confidence {
  padding: .5rem;
  border: 2px solid $amber !important;
  border-radius: $radius-small;
  background: $amber-bg;
}

.confidence-note {
  grid-column: 1 / -1;
  color: $amber;
  font-size: .9375rem;
  font-weight: 700;
}

.evidence {
  padding: $space-3 0;
  border-bottom: 1px solid $line;
}

.evidence h2,
.evidence p {
  margin: 0;
}

.evidence > p,
.evidence-details {
  margin-top: $space-1;
  color: $muted;
}

.evidence-details {
  display: grid;
  gap: $space-1;
}

.audio-action {
  display: grid;
  gap: $space-1;
  margin-top: $space-1;
  color: $ink;
  font-weight: 700;
}

.audio-action audio {
  width: 100%;
  min-height: $control-height;
}

.evidence-action {
  display: inline-flex;
  align-items: center;
  min-height: $control-height;
  margin-top: $space-1;
  color: $primary;
  font-weight: 700;
}

.validation-errors {
  margin-top: $space-3;
  padding: $space-2;
  border: 1px solid $danger;
  border-radius: $radius-small;
}

.validation-errors h2,
.validation-errors p {
  margin: 0;
}

.validation-errors p + p {
  margin-top: .25rem;
}

footer {
  display: grid;
  gap: $space-2;
  margin-top: $space-4;
}

.confirm {
  border: 0;
  background: $primary;
  color: #fff;
  font-weight: 700;
}

.confirm:active {
  background: $primary-pressed;
}

.cancel {
  border: 1px solid $line;
  background: $surface;
  color: $ink;
}

@media (max-width: 28rem) {
  .summary label {
    grid-template-columns: 1fr;
  }
}
</style>
