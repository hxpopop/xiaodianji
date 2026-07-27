<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { apiClient } from '../../api/client'
import type { CustomerSummary } from '../../api/types'
import BottomNavigation from '../../components/BottomNavigation.vue'
import { recordStore } from '../../stores/record'

const customers = ref<CustomerSummary[]>([])
const loading = ref(true)
const error = ref('')

async function loadCustomers() {
  loading.value = true
  error.value = ''
  try {
    customers.value = await apiClient.getCustomers(recordStore.state.shopId)
  } catch (reason) {
    error.value = reason instanceof Error ? reason.message : '客户列表暂时无法加载。'
  } finally {
    loading.value = false
  }
}

function openCustomer(customer: CustomerSummary) {
  uni.navigateTo({
    url: `/pages/customer-detail/index?id=${encodeURIComponent(customer.id)}&name=${encodeURIComponent(customer.name)}`,
  })
}

onMounted(loadCustomers)
</script>

<template>
  <main class="page">
    <header>
      <p class="eyebrow">客户</p>
      <h1>客户账目</h1>
      <p>名称和别名来自已经确认的客户资料。</p>
    </header>

    <p v-if="loading" class="state" aria-live="polite">正在加载客户…</p>
    <p v-else-if="error" class="error" role="alert">{{ error }}</p>
    <p v-else-if="customers.length === 0" class="state">还没有客户资料。</p>

    <section v-else class="customer-list" aria-label="客户列表">
      <button
        v-for="customer in customers"
        :key="customer.id"
        type="button"
        @click="openCustomer(customer)"
      >
        <span>
          <strong>{{ customer.name }}</strong>
          <small v-if="customer.aliases.length">别名：{{ customer.aliases.join('、') }}</small>
        </span>
        <span class="link-label">查看账目</span>
      </button>
    </section>
  </main>
  <BottomNavigation active="customers" />
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
.state {
  margin: 0;
}

.eyebrow,
header p,
.state {
  color: $muted;
}

h1 {
  margin: .15rem 0 .35rem;
  font-size: 2rem;
}

.state,
.error {
  margin-top: $space-4;
}

.error {
  color: $danger;
}

.customer-list {
  margin-top: $space-4;
  border-top: 1px solid $line;
}

.customer-list button {
  display: flex;
  align-items: center;
  justify-content: space-between;
  width: 100%;
  min-height: 4.5rem;
  gap: $space-3;
  padding: $space-2 0;
  border: 0;
  border-bottom: 1px solid $line;
  border-radius: 0;
  background: $surface;
  color: $ink;
  text-align: left;
}

.customer-list button > span:first-child {
  display: grid;
}

small {
  color: $muted;
}

.link-label {
  flex: none;
  color: $primary;
  font-weight: 700;
}
</style>
