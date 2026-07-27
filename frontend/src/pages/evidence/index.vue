<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { apiClient } from '../../api/client'
import type { EvidenceRead } from '../../api/types'
import { recordStore } from '../../stores/record'

const evidence = ref<EvidenceRead | null>(null)
const loading = ref(false)
const error = ref('')
const actionMessage = ref('')

async function loadEvidence(evidenceId: string) {
  if (!evidenceId) {
    error.value = '缺少凭证编号，请返回查询结果重新打开。'
    return
  }
  loading.value = true
  error.value = ''
  actionMessage.value = ''
  try {
    evidence.value = await apiClient.getEvidence(recordStore.state.shopId, evidenceId)
  } catch (reason) {
    error.value = reason instanceof Error ? reason.message : '凭证暂时无法加载。'
  } finally {
    loading.value = false
  }
}

function previewImage() {
  const url = evidence.value?.access_url
  if (!url) return
  uni.previewImage({ current: url, urls: [url] })
}

function openRemoteEvidence() {
  const url = evidence.value?.access_url
  if (!url) return
  if (typeof window !== 'undefined' && typeof window.open === 'function') {
    window.open(url, '_blank', 'noopener,noreferrer')
    return
  }
  actionMessage.value = '正在下载原始文件…'
  uni.downloadFile({
    url,
    success(result) {
      if (result.statusCode < 200 || result.statusCode >= 300) {
        actionMessage.value = '下载失败，请稍后重试。'
        return
      }
      actionMessage.value = '下载完成，正在打开文件。'
      uni.openDocument({
        filePath: result.tempFilePath,
        showMenu: true,
        fail() {
          actionMessage.value = '文件已下载，但当前设备不能直接打开此格式。'
        },
      })
    },
    fail() {
      actionMessage.value = '下载失败，请检查网络后重试。'
    },
  })
}

defineExpose({ loadEvidence })

onMounted(() => {
  if (typeof getCurrentPages !== 'function') return
  const pages = getCurrentPages()
  const current = pages[pages.length - 1]
  const options = current?.$page?.options || current?.options
  void loadEvidence(String(options?.id || ''))
})
</script>

<template>
  <main class="page">
    <header>
      <p class="eyebrow">原始凭证</p>
      <h1>核对记录来源</h1>
      <p>凭证使用后端返回的短时访问链接。</p>
    </header>
    <p v-if="loading" class="state" aria-live="polite">正在加载凭证…</p>
    <p v-else-if="error" class="error" role="alert">{{ error }}</p>
    <article v-else-if="evidence" class="evidence">
      <dl>
        <dt>凭证类型</dt>
        <dd>{{ evidence.type === 'audio' ? '语音' : evidence.type === 'image' ? '图片' : '文字' }}</dd>
        <dt>原始文件</dt>
        <dd>{{ evidence.original_filename || '未提供文件名' }}</dd>
        <dt>处理状态</dt>
        <dd>{{ evidence.status }}</dd>
      </dl>
      <section v-if="evidence.type === 'audio'">
        <h2>原始音频</h2>
        <audio v-if="evidence.access_url" :src="evidence.access_url" controls />
        <p v-else class="state">音频访问链接暂不可用。</p>
        <p v-if="evidence.asr_text" class="transcript">{{ evidence.asr_text }}</p>
      </section>
      <section v-else-if="evidence.type === 'image'">
        <h2>原始图片</h2>
        <button v-if="evidence.access_url" type="button" data-action="preview-image" @click="previewImage">
          查看原始图片
        </button>
        <p v-else class="state">图片访问链接暂不可用。</p>
      </section>
      <section v-else>
        <h2>文字内容</h2>
        <p v-if="evidence.asr_text" class="transcript">{{ evidence.asr_text }}</p>
        <p v-else class="state">凭证没有可直接显示的文字内容。</p>
        <button v-if="evidence.access_url" type="button" data-action="open-remote" @click="openRemoteEvidence">
          打开或下载原始文本
        </button>
      </section>
      <p v-if="actionMessage" class="state" role="status">{{ actionMessage }}</p>
    </article>
  </main>
</template>

<style scoped lang="scss">
@use '../../styles/tokens.scss' as *;
.page{max-width:42rem;margin:auto;padding:$space-4 $space-3 calc($space-5 + env(safe-area-inset-bottom))}
.eyebrow,h1,header p,h2,p,dl,dt,dd{margin:0}.eyebrow,header p,.state,dt{color:$muted}
h1{margin:.15rem 0 .35rem;font-size:2rem}.state,.error,.evidence{margin-top:$space-4}.error{color:$danger}
dl{display:grid;grid-template-columns:6rem minmax(0,1fr);gap:$space-1 $space-2;padding:$space-3 0;border-top:1px solid $ink;border-bottom:1px solid $line}
section{display:grid;gap:$space-2;padding:$space-4 0;border-bottom:1px solid $line}h2{font-size:1.25rem}
audio{width:100%;min-height:3rem}.transcript{padding:$space-3;border-left:3px solid $primary;background:$surface}
button{width:100%;border:1px solid $line;background:$surface;color:$primary;font-weight:700}
</style>
