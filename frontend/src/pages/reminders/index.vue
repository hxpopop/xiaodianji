<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { apiClient } from '../../api/client'
import type { ReminderItem } from '../../api/types'
import ReminderCard from '../../components/ReminderCard.vue'
import { recordStore } from '../../stores/record'

const reminders = ref<ReminderItem[]>([])
const loading = ref(true)
const error = ref('')

async function loadReminders() {
  loading.value = true
  error.value = ''
  try {
    reminders.value = (await apiClient.getReminders(recordStore.state.shopId)).items
  } catch (reason) {
    error.value = reason instanceof Error ? reason.message : '逾期提醒暂时无法加载。'
  } finally {
    loading.value = false
  }
}

function openCustomer(reminder: ReminderItem) {
  uni.navigateTo({
    url: `/pages/customer-detail/index?id=${encodeURIComponent(reminder.customer_id)}&name=${encodeURIComponent(reminder.customer_name)}`,
  })
}

onMounted(loadReminders)
</script>

<template>
  <main class="page">
    <header>
      <p class="eyebrow">逾期提醒</p>
      <h1>需要跟进的账目</h1>
      <p>按后端当前未解决的提醒展示，不生成虚假示例。</p>
    </header>

    <p v-if="loading" class="state" aria-live="polite">正在加载逾期提醒…</p>
    <p v-else-if="error" class="error" role="alert">{{ error }}</p>
    <section v-else-if="reminders.length" class="list" aria-label="逾期提醒列表">
      <ReminderCard
        v-for="reminder in reminders"
        :key="reminder.customer_id"
        :reminder="reminder"
        @open-customer="openCustomer"
      />
    </section>
    <section v-else class="empty">
      <h2>目前没有逾期账目</h2>
      <p>这里会在产生真实逾期提醒后显示客户、余额和逾期天数。</p>
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
h2,
.empty p {
  margin: 0;
}

.eyebrow,
header p,
.state,
.empty p {
  color: $muted;
}

h1 {
  margin: .15rem 0 .35rem;
  font-size: 2rem;
}

.state,
.error,
.list,
.empty {
  margin-top: $space-4;
}

.error {
  color: $danger;
}

.list {
  border-top: 1px solid $ink;
}

.empty {
  padding: $space-4 0;
  border-top: 1px solid $line;
  border-bottom: 1px solid $line;
}

.empty p {
  margin-top: .25rem;
}
</style>
