<script setup lang="ts">
import { computed } from 'vue'
import type { LineItemDraft } from '../api/types'
type Field = 'product'|'spec'|'quantity'|'unit'|'unit_price'|'subtotal'
const props=defineProps<{item:LineItemDraft;index:number;lowConfidenceFields?:Partial<Record<Field,boolean>>}>()
const emit=defineEmits<{(event:'update:item',value:LineItemDraft):void}>()
const money=computed(()=>Number.isFinite(Number(props.item.subtotal))?Number(props.item.subtotal).toFixed(2):'—')
const labels:Record<Field,string>={product:'商品',spec:'规格',quantity:'数量',unit:'单位',unit_price:'单价',subtotal:'小计'}
function fieldPath(field:Field){return `items.${props.index}.${field}`}
function isLow(field:Field){return Boolean(props.lowConfidenceFields?.[field])}
function eventValue(event:Event&{detail?:{value?:string}}){return event.detail?.value??(event.target as HTMLInputElement).value}
function update(field:keyof LineItemDraft,value:string){
  const numeric=field==='quantity'||field==='unit_price'||field==='subtotal'
  emit('update:item',{...props.item,[field]:numeric?(value.trim()===''?Number.NaN:Number(value)):value})
}
</script>
<template>
  <section class="line-item" :aria-label="`商品 ${index+1}`">
    <label :data-field="fieldPath('product')" :class="{'is-low-confidence':isLow('product')}">
      <span>商品</span><input :value="item.product" @input="update('product',eventValue($event))">
      <span v-if="isLow('product')" class="confidence-note">商品识别把握较低，请核对商品</span>
    </label>
    <label :data-field="fieldPath('spec')" :class="{'is-low-confidence':isLow('spec')}">
      <span>规格</span><input :value="item.spec??''" placeholder="选填" @input="update('spec',eventValue($event))">
      <span v-if="isLow('spec')" class="confidence-note">规格识别把握较低，请核对规格</span>
    </label>
    <div class="numeric-fields">
      <label v-for="field in (['quantity','unit','unit_price'] as const)" :key="field" :data-field="fieldPath(field)" :class="{'is-low-confidence':isLow(field)}">
        <span>{{ field==='unit_price'?'单价（元）':labels[field] }}</span>
        <input :type="field==='unit'?'text':'number'" :min="field==='quantity'?'0.001':field==='unit_price'?'0':undefined" :step="field==='quantity'?'0.001':field==='unit_price'?'0.01':undefined" :value="item[field]??''" @input="update(field,eventValue($event))">
        <span v-if="isLow(field)" class="confidence-note">{{ labels[field] }}识别把握较低，请核对{{ labels[field] }}</span>
      </label>
    </div>
    <div class="subtotal" :data-field="fieldPath('subtotal')" :class="{'is-low-confidence':isLow('subtotal')}">
      <span>小计</span><strong>¥{{ money }}</strong>
      <span v-if="isLow('subtotal')" class="confidence-note">小计识别把握较低，请核对小计</span>
    </div>
  </section>
</template>
<style scoped lang="scss">
@use '../styles/tokens.scss' as *;
.line-item{padding:$space-3 0;border-top:1px solid $line;display:grid;gap:$space-2}label,.subtotal{display:grid;gap:.25rem;font-weight:600}
.numeric-fields{display:grid;grid-template-columns:minmax(0,1fr) minmax(5rem,.7fr) minmax(0,1fr);gap:$space-2}
input{width:100%;min-height:$control-height;padding:0 .75rem;border:1px solid $line;border-radius:$radius-small;background:$surface;color:$ink}
.subtotal{grid-template-columns:1fr auto;align-items:baseline}.is-low-confidence{margin:0 -.5rem;padding:.5rem;border:2px solid $amber;border-radius:$radius-small;background:$amber-bg}
.confidence-note{grid-column:1/-1;color:$amber;font-size:.9375rem;font-weight:700}
@media(max-width:30rem){.numeric-fields{grid-template-columns:1fr 1fr}.numeric-fields label:last-child{grid-column:1/-1}}
</style>
