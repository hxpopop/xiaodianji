<script setup lang="ts">
import { computed } from 'vue'
import type { LineItemDraft } from '../api/types'

type LineItemField = 'product' | 'spec' | 'quantity' | 'unit' | 'unit_price' | 'subtotal'

const props = defineProps<{
  item: LineItemDraft
  index: number
  lowConfidenceFields?: Partial<Record<LineItemField, boolean>>
}>()
const emit = defineEmits<{ (event: 'update:item', value: LineItemDraft): void }>()

const money = computed(() => Number.isFinite(Number(props.item.subtotal))
  ? Number(props.item.subtotal).toFixed(2)
  : '—')
const warnings: Record<LineItemField, string> = {
  product: '商品识别把握较低，请核对商品',
  spec: '规格识别把握较低，请核对规格',
  quantity: '数量识别把握较低，请核对数量',
  unit: '单位识别把握较低，请核对单位',
  unit_price: '单价识别把握较低，请核对单价',
  subtotal: '小计识别把握较低，请核对小计',
}

function fieldPath(field: LineItemField) {
  return `items.${props.index}.${field}`
}

function isLowConfidence(field: LineItemField) {
  return Boolean(props.lowConfidenceFields?.[field])
}

function update(field: keyof LineItemDraft, value: string) {
  const numeric = field === 'quantity' || field === 'unit_price' || field === 'subtotal'
  const parsed = value.trim() === '' ? Number.NaN : Number(value)
  emit('update:item', { ...props.item, [field]: numeric ? parsed : value })
}
</script>

<template>
  <section class="line-item" :aria-label="`商品 ${index + 1}`">
    <label
      :data-field="fieldPath('product')"
      :class="{ 'is-low-confidence': isLowConfidence('product') }"
    >
      <span>商品</span>
      <input
        :value="item.product"
        @input="update('product', ($event.target as HTMLInputElement).value)"
      />
      <span v-if="isLowConfidence('product')" class="confidence-note">{{ warnings.product }}</span>
    </label>

    <label
      :data-field="fieldPath('spec')"
      :class="{ 'is-low-confidence': isLowConfidence('spec') }"
    >
      <span>规格</span>
      <input
        :value="item.spec ?? ''"
        placeholder="选填"
        @input="update('spec', ($event.target as HTMLInputElement).value)"
      />
      <span v-if="isLowConfidence('spec')" class="confidence-note">{{ warnings.spec }}</span>
    </label>

    <div class="numeric-fields">
      <label
        :data-field="fieldPath('quantity')"
        :class="{ 'is-low-confidence': isLowConfidence('quantity') }"
      >
        <span>数量</span>
        <input
          type="number"
          min="0.001"
          step="0.001"
          required
          :value="item.quantity"
          @input="update('quantity', ($event.target as HTMLInputElement).value)"
        />
        <span v-if="isLowConfidence('quantity')" class="confidence-note">{{ warnings.quantity }}</span>
      </label>

      <label
        :data-field="fieldPath('unit')"
        :class="{ 'is-low-confidence': isLowConfidence('unit') }"
      >
        <span>单位</span>
        <input
          :value="item.unit"
          @input="update('unit', ($event.target as HTMLInputElement).value)"
        />
        <span v-if="isLowConfidence('unit')" class="confidence-note">{{ warnings.unit }}</span>
      </label>

      <label
        :data-field="fieldPath('unit_price')"
        :class="{ 'is-low-confidence': isLowConfidence('unit_price') }"
      >
        <span>单价（元）</span>
        <input
          type="number"
          min="0"
          step="0.01"
          required
          :value="item.unit_price"
          @input="update('unit_price', ($event.target as HTMLInputElement).value)"
        />
        <span v-if="isLowConfidence('unit_price')" class="confidence-note">{{ warnings.unit_price }}</span>
      </label>
    </div>

    <div
      class="subtotal"
      :data-field="fieldPath('subtotal')"
      :class="{ 'is-low-confidence': isLowConfidence('subtotal') }"
    >
      <span>小计</span>
      <strong>¥{{ money }}</strong>
      <span v-if="isLowConfidence('subtotal')" class="confidence-note">{{ warnings.subtotal }}</span>
    </div>
  </section>
</template>

<style scoped lang="scss">
@use '../styles/tokens.scss' as *;

.line-item {
  padding: $space-3 0;
  border-top: 1px solid $line;
  display: grid;
  gap: $space-2;
}

label,
.subtotal {
  display: grid;
  gap: .25rem;
  font-weight: 600;
}

.numeric-fields {
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(5rem, .7fr) minmax(0, 1fr);
  gap: $space-2;
}

input {
  width: 100%;
  min-height: $control-height;
  padding: 0 .75rem;
  border: 1px solid $line;
  border-radius: $radius-small;
  background: $surface;
  color: $ink;
}

.subtotal {
  grid-template-columns: 1fr auto;
  align-items: baseline;
}

.is-low-confidence {
  margin: 0 -.5rem;
  padding: .5rem;
  border: 2px solid $amber;
  border-radius: $radius-small;
  background: $amber-bg;
}

.confidence-note {
  grid-column: 1 / -1;
  color: $amber;
  font-size: .9375rem;
  font-weight: 700;
}

@media (max-width: 30rem) {
  .numeric-fields {
    grid-template-columns: 1fr 1fr;
  }

  .numeric-fields label:last-child {
    grid-column: 1 / -1;
  }
}
</style>
