<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import type { ConfirmationRead, QuoteDraft, RecordDraft, TransactionDraft } from '../api/types'
import LineItemEditor from './LineItemEditor.vue'

type ItemRecordDraft = QuoteDraft | TransactionDraft

const props = withDefaults(defineProps<{ confirmation: ConfirmationRead; confidenceThreshold?: number }>(), { confidenceThreshold: 0.75 })
const emit = defineEmits<{ (event: 'confirm', payload: { draft: RecordDraft; edited: boolean }): void; (event: 'cancel'): void }>()
const clone = <T>(value: T): T => JSON.parse(JSON.stringify(value)) as T
const initial = JSON.stringify(props.confirmation.effective_json)
const draft = ref<RecordDraft>(clone(props.confirmation.effective_json))
watch(() => props.confirmation, value => { draft.value = clone(value.effective_json) }, { deep: true })
const itemDraft = computed<ItemRecordDraft | null>(() => draft.value.target_type === 'payment' ? null : draft.value)
const dateLabel = computed(() => draft.value.target_type === 'quote' ? '报价日期' : draft.value.target_type === 'payment' ? '收款日期' : '交易日期')
const dateValue = computed(() => draft.value.target_type === 'quote' ? draft.value.quoted_at : draft.value.target_type === 'payment' ? draft.value.paid_at : draft.value.occurred_at)
const total = computed(() => draft.value.target_type === 'payment' ? draft.value.amount : draft.value.total_amount)
const evidenceId = computed(() => draft.value.source_evidence_id)
function confidenceBelow(path: string) { return Number(props.confirmation.field_confidences[path] || 1) < props.confidenceThreshold }
function updateItem(index: number, item: TransactionDraft['items'][number]) {
  const current = draft.value
  if (current.target_type === 'payment') return
  const items = [...current.items]
  items[index] = { ...item, subtotal: Number((item.quantity * item.unit_price).toFixed(2)) }
  draft.value = { ...current, items, total_amount: Number(items.reduce((sum, line) => sum + line.subtotal, 0).toFixed(2)) }
}
function submit() { emit('confirm', { draft: draft.value, edited: JSON.stringify(draft.value) !== initial }) }
</script>

<template>
  <article class="confirmation-card" aria-labelledby="confirmation-heading">
    <header><p class="eyebrow">请核对后再记账</p><h1 id="confirmation-heading">确认这笔记录</h1></header>
    <dl class="summary"><div><dt>客户</dt><dd>{{ draft.customer_name }}</dd></div><div><dt>{{ dateLabel }}</dt><dd>{{ new Date(dateValue).toLocaleString('zh-CN', { dateStyle: 'medium', timeStyle: 'short' }) }}</dd></div><div v-if="draft.target_type === 'transaction'"><dt>付款状态</dt><dd>{{ draft.payment_status === 'unpaid' ? '赊账未收' : '已收款' }}</dd></div></dl>
    <section v-if="itemDraft" aria-labelledby="items-heading"><h2 id="items-heading">商品明细</h2><LineItemEditor v-for="(item, index) in itemDraft.items" :key="index" :item="item" :index="index" :low-confidence="confidenceBelow(`items.${index}.quantity`)" @update:item="updateItem(index, $event)" /></section>
    <section class="total"><span>合计</span><strong>¥{{ Number(total).toFixed(2) }}</strong></section>
    <section class="evidence" aria-label="原始凭证"><h2>原始凭证</h2><p>{{ evidenceId ? `凭证编号：${evidenceId}` : '本次没有关联原始凭证。' }}</p></section>
    <footer><button class="confirm" type="button" data-action="confirm" @click="submit">确认记账</button><button class="cancel" type="button" data-action="cancel" @click="emit('cancel')">取消这笔记录</button></footer>
  </article>
</template>

<style scoped lang="scss">
@use '../styles/tokens.scss' as *;
.confirmation-card { max-width: 42rem; margin: 0 auto; padding: $space-4 $space-3 calc($space-5 + env(safe-area-inset-bottom)); background: $surface; }
header { margin-bottom: $space-4; }.eyebrow { margin: 0 0 .25rem; color: $muted; font-size: .9375rem; }h1,h2 { letter-spacing: -.02em; }h1 { margin: 0; font-size: 2rem; line-height: 1.15; }h2 { font-size: 1.25rem; }
.summary { display: grid; gap: $space-2; margin: 0 0 $space-4; }.summary div { display: flex; justify-content: space-between; gap: $space-3; padding-bottom: $space-2; border-bottom: 1px solid $line; }dt { color: $muted; }dd { margin: 0; font-weight: 700; text-align: right; }
.total { display: flex; justify-content: space-between; align-items: baseline; margin: $space-4 0; padding: $space-3 0; border-top: 1px solid $ink; border-bottom: 1px solid $ink; }.total strong { font-size: $amount-text; letter-spacing: -.03em; }.evidence { padding: $space-3 0; border-bottom: 1px solid $line; }.evidence h2,.evidence p { margin: 0; }.evidence p { margin-top: .25rem; color: $muted; overflow-wrap: anywhere; }
footer { display: grid; gap: $space-2; margin-top: $space-4; }.confirm { border: 0; background: $primary; color: #fff; font-weight: 700; }.confirm:active { background: $primary-pressed; }.cancel { border: 1px solid $line; background: #fff; color: $ink; }
</style>
