<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { apiClient } from '../../api/client'
import { recordStore } from '../../stores/record'

const overdue = ref(0)
const reminderText = ref('正在查看逾期提醒…')
const unavailableNotice = ref('')

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

function showUnavailable(message: string) {
  unavailableNotice.value = message
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
      @click="showUnavailable('语音记账即将开放，请先选择文字记账或手动输入。')"
    >
      <strong>说一笔</strong>
      <span>语音记账即将开放</span>
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
        @click="showUnavailable('查欠款功能即将开放，请先查看下方逾期提醒。')"
      >
        <span>查欠款</span>
        <small>即将开放</small>
      </button>
    </section>

    <p v-if="unavailableNotice" class="unavailable-notice" role="status">
      {{ unavailableNotice }}
    </p>

    <section class="reminder" aria-live="polite">
      <div>
        <h2>逾期提醒</h2>
        <p>{{ reminderText }}</p>
      </div>
      <strong v-if="overdue">{{ overdue }} 位待跟进</strong>
    </section>
  </main>
</template>

<style scoped lang="scss">
@use '../../styles/tokens.scss' as *;

.home {
  max-width: 42rem;
  margin: auto;
  padding: $space-3 $space-3 calc($space-4 + env(safe-area-inset-bottom));
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

.unavailable-notice {
  margin: 0 0 $space-3;
  padding: $space-2;
  border-left: 3px solid $primary;
  color: $muted;
}

.reminder {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: $space-3;
  padding: $space-3 0;
  border-top: 1px solid $line;
}

.reminder h2,
.reminder p {
  margin: 0;
}

.reminder h2 {
  font-size: 1.25rem;
}

.reminder p {
  margin-top: .25rem;
  color: $muted;
}

.reminder strong {
  flex: none;
  color: $amber;
}
</style>
