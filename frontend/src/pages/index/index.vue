<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { apiClient } from '../../api/client'
import BottomNavigation from '../../components/BottomNavigation.vue'
import { recordStore } from '../../stores/record'

const overdue = ref(0)
const reminderText = ref('正在查看逾期提醒…')

onMounted(async () => {
  try {
    const summary = await apiClient.getReminders(recordStore.state.shopId)
    overdue.value = summary.overdue_count
    reminderText.value = overdue.value
      ? `有 ${overdue.value} 位客户存在逾期账目`
      : '目前没有逾期账目'
  } catch {
    reminderText.value = '暂时无法加载提醒，可稍后再试。'
  }
})

function go(path: string) {
  uni.navigateTo({ url: path })
}
</script>

<template>
  <main class="home">
    <header>
      <h1>小店记</h1>
      <p>把生意说清楚，账目由你最后确认。</p>
    </header>

    <button
      class="voice-action"
      type="button"
      data-action="voice"
      @click="go('/pages/record-voice/index')"
    >
      <strong>说一笔</strong>
      <span>语音生成确认单</span>
    </button>

    <section class="actions" aria-label="记账与查账方式">
      <button type="button" data-action="text" @click="go('/pages/record-text/index')">
        文字记账
      </button>
      <button type="button" data-action="manual" @click="go('/pages/record-manual/index')">
        手动输入
      </button>
      <button
        class="query-action"
        type="button"
        data-action="query"
        @click="go('/pages/query/index')"
      >
        <span>查欠款</span>
        <small>结论与凭证</small>
      </button>
    </section>

    <button class="reminder" type="button" @click="go('/pages/reminders/index')">
      <span>
        <strong>逾期提醒</strong>
        <small>{{ reminderText }}</small>
      </span>
      <b v-if="overdue">{{ overdue }} 位</b>
      <b v-else>查看</b>
    </button>
  </main>
  <BottomNavigation active="record" />
</template>

<style scoped lang="scss">
@use '../../styles/tokens.scss' as *;

.home {
  max-width: 42rem;
  margin: auto;
  padding: $space-3 $space-3 calc(5.5rem + env(safe-area-inset-bottom));
}

header {
  margin-bottom: $space-3;
}

h1 {
  margin: 0;
  font-size: 2rem;
  letter-spacing: -.04em;
  line-height: 1.1;
}

header p {
  margin: .25rem 0 0;
  color: $muted;
}

.voice-action {
  width: 100%;
  min-height: 7.5rem;
  display: grid;
  place-content: center;
  gap: .25rem;
  border: 0;
  background: $primary;
  color: #fff;
  text-align: center;
}

.voice-action strong {
  font-size: 2rem;
  letter-spacing: -.03em;
}

.voice-action span {
  font-size: .9375rem;
}

.voice-action:active {
  background: $primary-pressed;
}

.actions {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: $space-2;
  margin: $space-3 0;
}

.actions button {
  border: 1px solid $line;
  background: $surface;
  color: $ink;
  font-weight: 700;
}

.query-action {
  grid-column: 1 / -1;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: $space-2;
  padding: 0 $space-3;
}

.query-action small {
  color: $muted;
  font-weight: 600;
}

.reminder {
  display: flex;
  align-items: center;
  justify-content: space-between;
  width: 100%;
  min-height: 4.5rem;
  gap: $space-3;
  padding: $space-2 0;
  border: 0;
  border-top: 1px solid $line;
  border-bottom: 1px solid $line;
  border-radius: 0;
  background: $surface;
  color: $ink;
  text-align: left;
}

.reminder > span {
  display: grid;
}

.reminder small {
  color: $muted;
}

.reminder b {
  flex: none;
  color: $amber;
}
</style>
