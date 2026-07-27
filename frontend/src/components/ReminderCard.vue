<script setup lang="ts">
import type { ReminderItem } from '../api/types'

defineProps<{ reminder: ReminderItem }>()

const emit = defineEmits<{
  (event: 'open-customer', reminder: ReminderItem): void
}>()

function money(value: string | number) {
  const amount = Number(value)
  return Number.isFinite(amount) ? amount.toFixed(2) : String(value)
}
</script>

<template>
  <article class="reminder-card">
    <div>
      <p class="overdue">已逾期 {{ reminder.overdue_days }} 天</p>
      <h2>{{ reminder.customer_name }}</h2>
      <p>{{ reminder.overdue_transaction_count }} 笔逾期交易</p>
    </div>
    <div class="amount">
      <span>当前余额</span>
      <strong>¥{{ money(reminder.balance) }}</strong>
    </div>
    <button type="button" data-action="open-customer" @click="emit('open-customer', reminder)">
      查看明细
    </button>
  </article>
</template>

<style scoped lang="scss">
@use '../styles/tokens.scss' as *;

.reminder-card {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  gap: $space-2 $space-3;
  padding: $space-3 0;
  border-bottom: 1px solid $line;
}

h2,
p {
  margin: 0;
}

h2 {
  margin: .2rem 0;
  font-size: 1.25rem;
}

p,
.amount span {
  color: $muted;
}

.overdue {
  color: $amber;
  font-weight: 700;
}

.amount {
  display: grid;
  align-content: center;
  justify-items: end;
}

.amount strong {
  font-size: 1.25rem;
}

button {
  grid-column: 1 / -1;
  width: 100%;
  border: 1px solid $line;
  background: $surface;
  color: $primary;
  font-weight: 700;
}
</style>
