<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { apiClient } from '../../api/client'
import { recordStore } from '../../stores/record'
const overdue = ref(0)
const reminderText = ref('正在查看逾期提醒…')
onMounted(async () => { try { const summary = await apiClient.getReminders(recordStore.state.shopId); overdue.value = summary.overdue_count; reminderText.value = overdue.value ? `有 ${overdue.value} 位客户存在逾期账目` : '目前没有逾期账目'; } catch { reminderText.value = '暂时无法加载提醒，可稍后再试。' } })
function go(path: string) { uni.navigateTo({ url: path }) }
</script>
<template><main class="home"><header><h1>说一笔</h1><p>把生意说清楚，账目由你最后确认。</p></header><section class="actions" aria-label="记账方式"><button class="primary" @click="go('/pages/record-text/index')">文字记账</button><button @click="go('/pages/record-manual/index')">手动输入</button><button @click="go('/pages/record-text/index')">查欠款</button></section><section class="reminder" aria-live="polite"><h2>逾期提醒</h2><p>{{ reminderText }}</p><strong v-if="overdue">{{ overdue }} 位待跟进</strong></section></main></template>
<style scoped lang="scss">@use '../../styles/tokens.scss' as *;.home{max-width:42rem;margin:auto;padding:$space-5 $space-3 calc($space-5 + env(safe-area-inset-bottom));}h1{margin:0;font-size:2.5rem;letter-spacing:-.04em;line-height:1.1;}header p{color:$muted;}.actions{display:grid;gap:$space-2;margin:$space-5 0;}.actions button{border:1px solid $line;background:#fff;color:$ink;font-weight:700;}.actions .primary{border:0;background:$primary;color:#fff;}.reminder{padding:$space-4 0;border-top:1px solid $line;}.reminder h2,.reminder p{margin:0;}.reminder p{margin-top:.5rem;color:$muted;}.reminder strong{display:block;margin-top:$space-2;color:$amber;}</style>
