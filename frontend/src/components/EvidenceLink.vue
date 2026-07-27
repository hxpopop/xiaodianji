<script setup lang="ts">
defineProps<{
  evidenceId: string
  label?: string
}>()

const emit = defineEmits<{
  (event: 'open', evidenceId: string): void
}>()
</script>

<template>
  <button
    class="evidence-link"
    type="button"
    data-action="open-evidence"
    @click="emit('open', evidenceId)"
  >
    {{ label || '查看凭证' }}
  </button>
</template>

<style scoped lang="scss">
@use '../styles/tokens.scss' as *;

.evidence-link {
  min-height: 2.75rem;
  padding: 0 $space-2;
  border: 1px solid $line;
  background: $surface;
  color: $primary;
  font-weight: 700;
}
</style>
