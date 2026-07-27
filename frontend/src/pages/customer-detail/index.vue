<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { apiClient } from '../../api/client'
import type { QueryResponse } from '../../api/types'
import QueryResult from '../../components/QueryResult.vue'
import { recordStore } from '../../stores/record'

const customerId = ref('')
const customerName = ref('')
const result = ref<QueryResponse | null>(null)
const loading = ref(false)
const error = ref('')

async function loadCustomer(name: string, id = '') {
  customerName.value = name
  customerId.value = id
  if (!name) {
    error.value = '缺少客户名称，请返回客户列表重新选择。'
    return
  }
  loading.value = true
  error.value = ''
  try {
    result.value = await apiClient.query(recordStore.state.shopId, `${name}还欠多少钱`)
  } catch (reason) {
    error.value = reason instanceof Error ? reason.message : '客户账目暂时无法加载。'
  } finally {
    loading.value = false
  }
}

function openEvidence(evidenceId: string) {
  uni.navigateTo({ url: `/pages/evidence/index?id=${encodeURIComponent(evidenceId)}` })
}

defineExpose({ loadCustomer })

onMounted(() => {
  if (typeof getCurrentPages !== 'function') return
  const pages = getCurrentPages()
  const current = pages[pages.length - 1]
  const options = current?.$page?.options || current?.options
  void loadCustomer(String(options?.name || ''), String(options?.id || ''))
})
</script>

<template>
  <main class="page">
    <header>
      <p class="eyebrow">客户账目</p>
      <h1>{{ customerName || '客户详情' }}</h1>
      <p v-if="customerId">客户编号 {{ customerId }}</p>
    </header>
    <p v-if="loading" class="state" aria-live="polite">正在计算客户欠款…</p>
    <p v-else-if="error" class="error" role="alert">{{ error }}</p>
    <QueryResult v-else-if="result" :result="result" @open-evidence="openEvidence" />
  </main>
</template>

<style scoped lang="scss">
@use '../../styles/tokens.scss' as *;
.page{max-width:42rem;margin:auto;padding:$space-4 $space-3 calc($space-5 + env(safe-area-inset-bottom))}
.eyebrow,h1,header p{margin:0}.eyebrow,header p,.state{color:$muted}h1{margin:.15rem 0;font-size:2rem}
.state,.error{margin-top:$space-4}.error{color:$danger}
</style>
