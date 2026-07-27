<script setup lang="ts">
import ConfirmationCard from '../../components/ConfirmationCard.vue'
import { recordStore } from '../../stores/record'
const threshold = Number(import.meta.env.VITE_CONFIDENCE_THRESHOLD || .75)
async function confirm(payload: { draft: any; edited: boolean }) { try { await recordStore.resolveDraft(payload.draft, payload.edited); uni.reLaunch({ url: '/pages/index/index' }) } catch { /* actionable error remains visible below */ } }
async function cancel() { try { await recordStore.cancelDraft(); uni.reLaunch({ url: '/pages/index/index' }) } catch { /* actionable error remains visible below */ } }
</script>
<template><main><ConfirmationCard v-if="recordStore.state.draft" :confirmation="recordStore.state.draft" :confidence-threshold="threshold" @confirm="confirm" @cancel="cancel" /><section v-else class="empty"><h1>没有待确认的记录</h1><navigator url="/pages/record-manual/index">去手动输入</navigator></section><section v-if="recordStore.state.error" class="error" role="alert"><p>{{ recordStore.state.error }}</p><navigator url="/pages/record-manual/index">改用手动输入</navigator></section></main></template>
<style scoped lang="scss">@use '../../styles/tokens.scss' as *;.empty,.error{padding:$space-4 $space-3 calc($space-4 + env(safe-area-inset-bottom))}.error{color:$danger}.error navigator,.empty navigator{display:inline-flex;align-items:center;min-height:$control-height;color:$primary;font-weight:700}</style>
