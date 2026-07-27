<script setup lang="ts">
import { ref } from 'vue'
import { recordStore } from '../../stores/record'

const text = ref('')
const error = ref('')

async function submit() {
  error.value = ''
  try {
    await recordStore.createTextDraft(text.value)
    uni.navigateTo({ url: '/pages/confirmation/index' })
  } catch (reason) {
    error.value = reason instanceof Error ? reason.message : '识别失败，请手动输入。'
  }
}
</script>

<template>
  <main class="page">
    <h1>文字记账</h1>
    <label for="record-text">把客户、商品、数量和价格写下来</label>
    <textarea
      id="record-text"
      v-model="text"
      placeholder="例如：王老板赊账水泥五袋，每袋二十元"
    />
    <p v-if="error" class="error">{{ error }}</p>
    <button :disabled="!text.trim() || recordStore.state.saving" @click="submit">
      生成确认单
    </button>
    <navigator
      class="manual-fallback"
      data-action="manual-fallback"
      url="/pages/record-manual/index"
      aria-label="改用手动输入"
      tabindex="0"
    >
      识别不顺利？改用手动输入
    </navigator>
  </main>
</template>

<style scoped lang="scss">
@use '../../styles/tokens.scss' as *;

.page {
  max-width: 42rem;
  margin: auto;
  padding: $space-4 $space-3 calc($space-4 + env(safe-area-inset-bottom));
  display: grid;
  gap: $space-3;
}

h1 {
  margin: 0;
}

textarea {
  min-height: 11rem;
  padding: $space-3;
  border: 1px solid $line;
  border-radius: $radius-medium;
  resize: vertical;
}

button {
  border: 0;
  background: $primary;
  color: #fff;
  font-weight: 700;
}

.error {
  margin: 0;
  color: $danger;
}

.manual-fallback {
  display: inline-flex;
  align-items: center;
  width: fit-content;
  min-height: 2.75rem;
  color: $primary;
  font-weight: 700;
}

.manual-fallback:focus-visible {
  outline: 3px solid #8cc3ff;
  outline-offset: 2px;
  border-radius: .25rem;
}
</style>
