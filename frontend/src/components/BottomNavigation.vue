<script setup lang="ts">
type Destination = 'record' | 'query' | 'customers' | 'mine'

defineProps<{ active: Destination }>()

const destinations: Array<{ key: Destination; label: string; url: string }> = [
  { key: 'record', label: '记账', url: '/pages/index/index' },
  { key: 'query', label: '查账', url: '/pages/query/index' },
  { key: 'customers', label: '客户', url: '/pages/customers/index' },
  { key: 'mine', label: '我的', url: '/pages/evaluation/index' },
]

function go(url: string) {
  uni.reLaunch({ url })
}
</script>

<template>
  <nav class="bottom-navigation" aria-label="主要导航">
    <button
      v-for="destination in destinations"
      :key="destination.key"
      type="button"
      :data-nav="destination.key"
      :aria-current="active === destination.key ? 'page' : undefined"
      :disabled="active === destination.key"
      @click="go(destination.url)"
    >
      {{ destination.label }}
    </button>
  </nav>
</template>

<style scoped lang="scss">
@use '../styles/tokens.scss' as *;

.bottom-navigation {
  position: fixed;
  z-index: 10;
  right: 0;
  bottom: 0;
  left: 0;
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  padding: .25rem max($space-1, env(safe-area-inset-right))
    calc(.25rem + env(safe-area-inset-bottom))
    max($space-1, env(safe-area-inset-left));
  border-top: 1px solid $line;
  background: rgba(255, 255, 255, .98);
}

button {
  min-height: 3rem;
  padding: 0 .25rem;
  border: 0;
  background: transparent;
  color: $muted;
  font-size: .875rem;
  font-weight: 700;
}

button[aria-current='page'] {
  color: $primary;
}

button:disabled {
  cursor: default;
  opacity: 1;
}

@media (prefers-reduced-motion: reduce) {
  button:active {
    transform: none;
  }
}
</style>
