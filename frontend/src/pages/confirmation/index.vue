<script setup lang="ts">
import ConfirmationCard from '../../components/ConfirmationCard.vue'
import { recordStore } from '../../stores/record'
const threshold = Number(import.meta.env.VITE_CONFIDENCE_THRESHOLD || .75)
async function confirm(payload: { draft: any; edited: boolean }) { try { if (payload.edited) await recordStore.updateDraft(payload.draft); await recordStore.confirmDraft(); uni.reLaunch({ url: '/pages/index/index' }) } catch { /* message remains visible below */ } }
async function cancel() { try { await recordStore.cancelDraft(); uni.reLaunch({ url: '/pages/index/index' }) } catch { /* message remains visible below */ } }
</script>
<template><main><ConfirmationCard v-if="recordStore.state.draft" :confirmation="recordStore.state.draft" :confidence-threshold="threshold" @confirm="confirm" @cancel="cancel" /><section v-else class="empty"><h1>没有待确认的记录</h1><navigator url="/pages/record-manual/index">去手动输入</navigator></section><p v-if="recordStore.state.error" class="error" role="alert">{{ recordStore.state.error }}</p></main></template>
<style scoped lang="scss">@use '../../styles/tokens.scss' as *;.empty{padding:$space-5 $space-3;}.error{max-width:42rem;margin:0 auto;padding:$space-3;color:$danger;}</style>
