<script setup lang="ts">
import type { LineItemDraft } from '../api/types'

const props = defineProps<{ item: LineItemDraft; index: number; lowConfidence?: boolean }>()
const emit = defineEmits<{ (event: 'update:item', value: LineItemDraft): void }>()

function update(field: keyof LineItemDraft, value: string) {
  const numeric = ['quantity', 'unit_price', 'subtotal'].includes(field)
  emit('update:item', { ...props.item, [field]: numeric ? Number(value) : value })
}
</script>

<template>
  <section class="line-item" :aria-label="`商品 ${index + 1}`">
    <label>商品<input :value="item.product" @input="update('product', ($event.target as HTMLInputElement).value)" /></label>
    <label :data-field="`items.${index}.quantity`" :class="{ 'is-low-confidence': lowConfidence }">
      数量<input type="number" min="0" step="0.001" :value="item.quantity" @input="update('quantity', ($event.target as HTMLInputElement).value)" />
      <span v-if="lowConfidence" class="confidence-note">识别把握较低，请核对数量</span>
    </label>
    <label>单位<input :value="item.unit" @input="update('unit', ($event.target as HTMLInputElement).value)" /></label>
    <label>单价（元）<input type="number" min="0" step="0.01" :value="item.unit_price" @input="update('unit_price', ($event.target as HTMLInputElement).value)" /></label>
    <p>小计：¥{{ item.subtotal.toFixed(2) }}</p>
  </section>
</template>

<style scoped lang="scss">
@use '../styles/tokens.scss' as *;
.line-item { padding: $space-3 0; border-top: 1px solid $line; display: grid; gap: $space-2; }
label { display: grid; gap: .25rem; font-weight: 600; }
input { width: 100%; min-height: 2.75rem; padding: 0 .75rem; border: 1px solid $line; border-radius: $radius-small; background: #fff; color: $ink; }
.is-low-confidence { margin: 0 -.5rem; padding: .5rem; border: 2px solid $amber; border-radius: $radius-small; background: $amber-bg; }
.confidence-note { color: $amber; font-weight: 700; font-size: .9375rem; }
p { margin: 0; color: $muted; }
</style>
