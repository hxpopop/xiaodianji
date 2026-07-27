<script setup lang="ts">
import { computed, ref } from 'vue'
import { apiClient } from '../../api/client'
import type { EvaluationRunRead, EvaluationScore } from '../../api/types'
import BottomNavigation from '../../components/BottomNavigation.vue'
import { recordStore } from '../../stores/record'

const run = ref<EvaluationRunRead | null>(null)
const loading = ref(false)
const error = ref('')

const scoreRows = computed<Array<{ label: string; score: EvaluationScore }>>(() => (
  run.value
    ? [
        { label: '客户', score: run.value.metrics.customer },
        { label: '商品', score: run.value.metrics.products },
        { label: '数量', score: run.value.metrics.quantities },
        { label: '金额', score: run.value.metrics.amounts },
        { label: '付款状态', score: run.value.metrics.payment_status },
      ]
    : []
))

function percent(value: string | number) {
  const accuracy = Number(value)
  return Number.isFinite(accuracy) ? `${(accuracy * 100).toFixed(1)}%` : '—'
}

function milliseconds(value: string | number) {
  const latency = Number(value)
  return Number.isFinite(latency) ? `${latency.toFixed(1)} ms` : '—'
}

async function runEvaluation() {
  if (loading.value || !recordStore.state.shopId) return
  loading.value = true
  error.value = ''
  try {
    run.value = await apiClient.runEvaluation(recordStore.state.shopId)
  } catch (reason) {
    error.value = reason instanceof Error ? reason.message : '评测暂时无法运行。'
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <main class="page">
    <header>
      <p class="eyebrow">我的 · 识别评测</p>
      <h1>固定样本评测</h1>
      <p>结果来自后端评测接口，不展示推测或占位指标。</p>
    </header>

    <button
      class="run-action"
      type="button"
      data-action="run-evaluation"
      :disabled="loading || !recordStore.state.shopId"
      @click="runEvaluation"
    >
      {{ loading ? '正在运行评测…' : '运行固定评测' }}
    </button>
    <p v-if="!recordStore.state.shopId" class="state">
      尚未配置商户，评测操作当前不可用。
    </p>
    <p v-if="error" class="error" role="alert">{{ error }}</p>

    <section v-if="run" class="summary" aria-labelledby="summary-heading">
      <h2 id="summary-heading">本次概览</h2>
      <dl>
        <div>
          <dt>样本量</dt>
          <dd>{{ run.case_count }}</dd>
        </div>
        <div>
          <dt>失败样本</dt>
          <dd>{{ run.failed_case_count }}</dd>
        </div>
        <div>
          <dt>平均时延</dt>
          <dd>{{ milliseconds(run.average_latency_ms) }}</dd>
        </div>
      </dl>
    </section>

    <section v-if="run" class="scores" aria-labelledby="scores-heading">
      <h2 id="scores-heading">字段准确率</h2>
      <div v-for="row in scoreRows" :key="row.label" class="score-row">
        <span>{{ row.label }}</span>
        <strong>{{ percent(row.score.accuracy) }}</strong>
        <small>分子 {{ row.score.correct }} / 分母 {{ row.score.total }}</small>
      </div>
    </section>

    <section v-else-if="!loading" class="empty">
      <h2>尚未运行评测</h2>
      <p>点击上方按钮后，将显示准确率、分子、分母、样本量和平均时延。</p>
    </section>
  </main>
  <BottomNavigation active="mine" />
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
h2,
p,
dl,
dt,
dd {
  margin: 0;
}

.eyebrow,
header p,
.state,
.empty p,
dt,
small {
  color: $muted;
}

h1 {
  margin: .15rem 0 .35rem;
  font-size: 2rem;
}

.run-action {
  width: 100%;
  margin-top: $space-4;
  border: 0;
  background: $primary;
  color: #fff;
  font-weight: 700;
}

.run-action:disabled {
  background: #e8ebf0;
  color: $muted;
  cursor: not-allowed;
}

.state,
.error {
  margin-top: $space-2;
}

.error {
  color: $danger;
}

.summary,
.scores,
.empty {
  margin-top: $space-4;
  padding-top: $space-3;
  border-top: 1px solid $ink;
}

h2 {
  margin-bottom: $space-2;
  font-size: 1.25rem;
}

.summary dl {
  display: grid;
  gap: $space-1;
}

.summary dl div,
.score-row {
  display: grid;
  grid-template-columns: 1fr auto;
  gap: .15rem $space-2;
  padding: $space-2 0;
  border-bottom: 1px solid $line;
}

.score-row small {
  grid-column: 1 / -1;
}

.empty p {
  margin-top: .25rem;
}
</style>
