<script setup lang="ts">
import { ref } from 'vue'
import { apiClient } from '../../api/client'
import type { QueryResponse } from '../../api/types'
import BottomNavigation from '../../components/BottomNavigation.vue'
import QueryResult from '../../components/QueryResult.vue'
import { recordStore } from '../../stores/record'

const examples = [
  '王老板还欠多少钱',
  '上次给王老板报的插座多少钱',
  '今天一共卖了多少',
  '哪些账逾期了',
  '有哪些待确认',
  '最近有哪些异常',
]

const question = ref('')
const result = ref<QueryResponse | null>(null)
const loading = ref(false)
const error = ref('')

async function submit(nextQuestion = question.value) {
  const normalized = nextQuestion.trim()
  if (!normalized || loading.value) return
  question.value = normalized
  loading.value = true
  error.value = ''
  result.value = null
  try {
    result.value = await apiClient.query(recordStore.state.shopId, normalized)
  } catch (reason) {
    error.value = reason instanceof Error ? reason.message : '查询暂时不可用，请稍后重试。'
  } finally {
    loading.value = false
  }
}

function openEvidence(evidenceId: string) {
  uni.navigateTo({ url: `/pages/evidence/index?id=${encodeURIComponent(evidenceId)}` })
}
</script>

<template>
  <main class="page">
    <header>
      <p class="eyebrow">查账</p>
      <h1>问一笔明白账</h1>
      <p>结论、计算口径、明细和原始凭证会一起展示。</p>
    </header>

    <section class="query-form" aria-label="输入查询问题">
      <p class="form-label">输入问题</p>
      <textarea
        id="query-question"
        v-model="question"
        placeholder="例如：王老板还欠多少钱"
      />
      <div
        class="submit-action"
        role="button"
        tabindex="0"
        :aria-disabled="!question.trim() || loading"
        @click="submit()"
        @keydown.enter="submit()"
        @keydown.space.prevent="submit()"
      >
        开始查询
      </div>
    </section>

    <section class="examples" aria-labelledby="examples-heading">
      <h2 id="examples-heading">六类示例问题</h2>
      <div
        v-for="example in examples"
        :key="example"
        class="example-action"
        role="button"
        tabindex="0"
        :aria-disabled="loading"
        @click="submit(example)"
        @keydown.enter="submit(example)"
        @keydown.space.prevent="submit(example)"
      >
        {{ example }}
      </div>
    </section>

    <p v-if="error" class="error" role="alert">{{ error }}</p>
    <QueryResult v-if="result" :result="result" @open-evidence="openEvidence" />
  </main>
  <BottomNavigation active="query" />
</template>

<style scoped lang="scss">
@use '../../styles/tokens.scss' as *;

.page {
  max-width: 42rem;
  margin: auto;
  padding: $space-3 $space-3 calc(5.5rem + env(safe-area-inset-bottom));
}

.eyebrow,
h1,
header p,
h2 {
  margin: 0;
}

.eyebrow,
header p {
  color: $muted;
}

h1 {
  margin: .15rem 0 .35rem;
  font-size: 2rem;
  letter-spacing: -.04em;
}

.query-form {
  display: grid;
  gap: $space-2;
  margin-top: $space-4;
}

.form-label,
h2 {
  font-weight: 700;
}

textarea {
  min-height: 7rem;
  padding: $space-2;
  border: 1px solid $line;
  border-radius: $radius-medium;
  background: $surface;
  resize: vertical;
}

.submit-action {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: $control-height;
  border-radius: $radius-small;
  border: 0;
  background: $primary;
  color: #fff;
  font-weight: 700;
}

.submit-action[aria-disabled='true'] {
  background: #e8ebf0;
  color: $muted;
}

.examples {
  display: grid;
  gap: $space-1;
  margin-top: $space-4;
}

.examples h2 {
  margin-bottom: .25rem;
  font-size: 1rem;
}

.example-action {
  display: flex;
  align-items: center;
  min-height: 2.75rem;
  border-bottom: 1px solid $line;
  color: $primary;
}

.example-action[aria-disabled='true'] {
  color: $muted;
}

.submit-action:focus-visible,
.example-action:focus-visible {
  outline: 3px solid #8cc3ff;
  outline-offset: 2px;
}

.error {
  padding: $space-2 0;
  color: $danger;
}
</style>
