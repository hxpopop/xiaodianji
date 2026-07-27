<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref } from 'vue'
import type { VoiceAudioInput } from '../../api/types'
import { recordStore } from '../../stores/record'

type RecordingStatus = 'idle' | 'recording' | 'paused' | 'uploading' | 'blocked'

const status = ref<RecordingStatus>('idle')
const elapsedSeconds = ref(0)
const permissionText = ref('等待麦克风授权')
const message = ref('点击开始后，说清客户、商品、数量、价格和付款状态。')
const showManualFallback = ref(false)
let recorder: UniRecorderManager | null = null
let timer: ReturnType<typeof setInterval> | null = null

const elapsedLabel = computed(() => {
  const minutes = Math.floor(elapsedSeconds.value / 60)
  const seconds = elapsedSeconds.value % 60
  return `${String(minutes).padStart(2, '0')}:${String(seconds).padStart(2, '0')}`
})

const primaryLabel = computed(() => {
  if (status.value === 'recording') return '结束并上传'
  if (status.value === 'paused') return '继续录音'
  if (status.value === 'uploading') return '正在识别…'
  if (status.value === 'blocked') return '录音不可用'
  return '开始录音'
})

function stopTimer() {
  if (timer !== null) {
    clearInterval(timer)
    timer = null
  }
}

function startTimer() {
  stopTimer()
  timer = setInterval(() => {
    elapsedSeconds.value += 1
  }, 1000)
}

function offerManual(messageText: string) {
  status.value = 'blocked'
  permissionText.value = '语音当前不可用'
  message.value = messageText
  showManualFallback.value = true
  stopTimer()
}

function setupRecorder() {
  const platform = typeof uni?.getSystemInfoSync === 'function'
    ? uni.getSystemInfoSync().uniPlatform
    : ''
  if (platform === 'web' || platform === 'h5') {
    offerManual('当前浏览器不支持录音，请改用结构化手动输入。')
    return
  }
  if (typeof uni === 'undefined' || typeof uni.getRecorderManager !== 'function') {
    offerManual('当前设备或浏览器不支持录音，请改用结构化手动输入。')
    return
  }
  recorder = uni.getRecorderManager()
  if (!recorder) {
    offerManual('当前设备或浏览器不支持录音，请改用结构化手动输入。')
    return
  }
  recorder.onStop(({ tempFilePath }) => {
    stopTimer()
    void submitRecordedAudio({
      path: tempFilePath,
      filename: 'recording.mp3',
      mimeType: 'audio/mpeg',
    })
  })
  recorder.onError(() => {
    offerManual('麦克风权限被拒绝或录音失败，请检查权限，或改用手动输入。')
  })
}

function startRecording() {
  if (!recorder) {
    offerManual('当前设备或浏览器不支持录音，请改用结构化手动输入。')
    return
  }
  showManualFallback.value = false
  elapsedSeconds.value = 0
  permissionText.value = '麦克风已启用'
  message.value = '正在录音，说完后点击“结束并上传”。'
  status.value = 'recording'
  recorder.start({
    duration: 60_000,
    format: 'mp3',
    sampleRate: 16_000,
    numberOfChannels: 1,
  })
  startTimer()
}

function pauseRecording() {
  if (!recorder || status.value !== 'recording') return
  recorder.pause()
  status.value = 'paused'
  message.value = '录音已暂停，可继续或直接取消后改用手动输入。'
  stopTimer()
}

function resumeRecording() {
  if (!recorder || status.value !== 'paused') return
  recorder.resume()
  status.value = 'recording'
  message.value = '正在继续录音。'
  startTimer()
}

function stopRecording() {
  if (!recorder || status.value !== 'recording') return
  status.value = 'uploading'
  message.value = '录音完成，正在上传并识别。'
  stopTimer()
  recorder.stop()
}

function handlePrimary() {
  if (status.value === 'recording') {
    stopRecording()
  } else if (status.value === 'paused') {
    resumeRecording()
  } else if (status.value !== 'uploading') {
    startRecording()
  }
}

async function submitRecordedAudio(audio: VoiceAudioInput) {
  showManualFallback.value = false
  status.value = 'uploading'
  message.value = '正在上传并识别，请稍候。'
  try {
    await recordStore.createVoiceDraft(audio)
    uni.navigateTo({ url: '/pages/confirmation/index' })
  } catch (reason) {
    const fallback = (
      typeof reason === 'object'
      && reason !== null
      && 'fallback' in reason
      && reason.fallback === 'manual_form'
    )
    offerManual(
      fallback
        ? '语音识别暂时不可用，原录音不会直接入账，请改用手动输入。'
        : '语音上传未完成，请重试或改用手动输入。',
    )
  }
}

defineExpose({ submitRecordedAudio })

onMounted(setupRecorder)
onUnmounted(stopTimer)
</script>

<template>
  <main class="page">
    <header>
      <p class="eyebrow">语音记账</p>
      <h1>说清楚，再确认</h1>
      <p>{{ message }}</p>
    </header>

    <section class="recorder" :class="{ 'is-recording': status === 'recording' }">
      <span class="permission">{{ permissionText }}</span>
      <strong class="duration" aria-label="录音时长">{{ elapsedLabel }}</strong>
      <button
        type="button"
        :class="['primary', { 'is-blocked': status === 'blocked' }]"
        data-action="record-primary"
        :disabled="status === 'uploading' || status === 'blocked'"
        @click="handlePrimary"
      >
        {{ primaryLabel }}
      </button>
      <button
        v-if="status === 'recording'"
        type="button"
        class="secondary"
        data-action="pause"
        @click="pauseRecording"
      >
        暂停录音
      </button>
    </section>

    <navigator
      v-if="showManualFallback"
      class="manual-fallback"
      data-action="manual-fallback"
      url="/pages/record-manual/index"
      aria-label="改用手动输入"
      tabindex="0"
    >
      改用手动输入
    </navigator>

    <section class="privacy">
      <h2>录音说明</h2>
      <p>语音只用于生成待确认记录；你点击“确认记账”前不会写入正式账本。</p>
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
.privacy p {
  margin: 0;
}

.eyebrow,
header p,
.privacy p {
  color: $muted;
}

h1 {
  margin: .2rem 0 .35rem;
  font-size: 2rem;
  letter-spacing: -.04em;
}

.recorder {
  display: grid;
  gap: $space-2;
  margin: $space-5 0 $space-3;
  padding: $space-4 0;
  border-top: 1px solid $line;
  border-bottom: 1px solid $line;
  text-align: center;
}

.permission {
  color: $muted;
}

.duration {
  font-variant-numeric: tabular-nums;
  font-size: 3rem;
  letter-spacing: -.04em;
}

.primary {
  border: 0;
  background: $primary;
  color: #fff;
  font-weight: 700;
}

.primary:active {
  background: $primary-pressed;
}

.primary:disabled,
.primary.is-blocked {
  background: #e8ebf0;
  color: $muted;
  cursor: not-allowed;
}

.secondary {
  border: 1px solid $line;
  background: $surface;
  color: $ink;
}

.manual-fallback {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 3rem;
  border: 1px solid $primary;
  border-radius: $radius-small;
  color: $primary;
  font-weight: 700;
}

.manual-fallback:focus-visible {
  outline: 3px solid #8cc3ff;
  outline-offset: 2px;
}

.privacy {
  margin-top: $space-4;
  padding-top: $space-3;
  border-top: 1px solid $line;
}

.privacy h2 {
  margin-bottom: .25rem;
  font-size: 1rem;
}
</style>
