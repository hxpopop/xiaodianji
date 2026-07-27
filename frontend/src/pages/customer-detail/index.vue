<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { getCustomerBalance } from '../../api/customerBalance'
import { recordStore } from '../../stores/record'

const customerId = ref('')
const customerName = ref('')
const balance = ref<string | number | null>(null)
const loading = ref(false)
const error = ref('')

const balanceLabel = computed(() => (
  balance.value === null ? '—' : `¥${Number(balance.value).toFixed(2)}`
))

async function loadCustomer(name: string, id = '') {
  customerName.value = name
  customerId.value = id
  balance.value = null
  if (!id) {
    error.value = '缺少客户编号，请返回客户列表重新选择。'
    return
  }
  loading.value = true
  error.value = ''
  try {
    const response = await getCustomerBalance(recordStore.state.shopId, id)
    balance.value = response.balance
  } catch (reason) {
    error.value = reason instanceof Error ? reason.message : '客户账目暂时无法加载。'
  } finally {
    loading.value = false
  }
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
    <section v-else class="balance" aria-label="客户当前欠款">
      <span>当前欠款</span>
      <strong>{{ balanceLabel }}</strong>
      <p>金额由已选客户编号对应的正式账目精确计算。</p>
    </section>
  </main>
</template>

<style scoped lang="scss">
@use '../../styles/tokens.scss' as *;

.page {
  max-width: 42rem;
  margin: auto;
  padding: $space-4 $space-3 calc($space-5 + env(safe-area-inset-bottom));
}

.eyebrow,
h1,
header p,
.balance p {
  margin: 0;
}

.eyebrow,
header p,
.state,
.balance span,
.balance p {
  color: $muted;
}

h1 {
  margin: .15rem 0;
  font-size: 2rem;
}

.state,
.error,
.balance {
  margin-top: $space-4;
}

.error {
  color: $danger;
}

.balance {
  display: grid;
  gap: $space-1;
  padding: $space-3 0;
  border-top: 1px solid $line;
  border-bottom: 1px solid $line;
}

.balance strong {
  font-size: 2.5rem;
  letter-spacing: -.04em;
}
</style>
