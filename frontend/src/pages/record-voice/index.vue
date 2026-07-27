<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref } from 'vue'
import type { VoiceAudioInput } from '../../api/types'
import { recordStore } from '../../stores/record'

type Status = 'idle' | 'recording' | 'paused' | 'uploading' | 'blocked'
const demoMode = import.meta.env.VITE_DEMO_MODE === 'true'
const showDemoAction = ref(false)
const status = ref<Status>('idle')
const elapsedSeconds = ref(0)
const permissionText = ref('等待麦克风授权')
const message = ref('点击开始后，说清客户、商品、数量、价格和付款状态。')
const showManualFallback = ref(false)
let recorder: UniRecorderManager | null = null
let timer: ReturnType<typeof setInterval> | null = null

const elapsedLabel = computed(() => `${String(Math.floor(elapsedSeconds.value / 60)).padStart(2, '0')}:${String(elapsedSeconds.value % 60).padStart(2, '0')}`)
const primaryLabel = computed(() => ({
  recording: '结束并上传',
  paused: '继续录音',
  uploading: '正在识别…',
  blocked: '录音不可用',
  idle: '开始录音',
}[status.value]))

function stopTimer() {
  if (timer !== null) clearInterval(timer)
  timer = null
}
function startTimer() {
  stopTimer()
  timer = setInterval(() => { elapsedSeconds.value += 1 }, 1000)
}
function offerManual(text: string) {
  status.value = 'blocked'
  permissionText.value = '语音当前不可用'
  message.value = text
  showManualFallback.value = true
  stopTimer()
}
function setupRecorder() {
  const platform = typeof uni?.getSystemInfoSync === 'function'
    ? uni.getSystemInfoSync().uniPlatform
    : ''
  if (platform === 'web' || platform === 'h5') {
    if (demoMode) {
      showDemoAction.value = true
      permissionText.value = '固定音频演示'
      message.value = '点击后使用固定评测音频；结果仍只进入待确认区。'
      return
    }
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
    void submitRecordedAudio({ path: tempFilePath, filename: 'recording.mp3', mimeType: 'audio/mpeg' })
  })
  recorder.onError(() => offerManual('麦克风权限被拒绝或录音失败，请检查权限，或改用手动输入。'))
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
  recorder.start({ duration: 60_000, format: 'mp3', sampleRate: 16_000, numberOfChannels: 1 })
  startTimer()
}
function pauseRecording() {
  if (!recorder || status.value !== 'recording') return
  recorder.pause()
  status.value = 'paused'
  message.value = '录音已暂停，可继续或改用手动输入。'
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
  if (status.value === 'recording') stopRecording()
  else if (status.value === 'paused') resumeRecording()
  else if (status.value !== 'uploading') startRecording()
}
async function submitDemoAudio() {
  await submitRecordedAudio(new Blob(['ID3xiaodianji-demo-audio'], { type: 'audio/mpeg' }))
}
async function submitRecordedAudio(audio: VoiceAudioInput) {
  showManualFallback.value = false
  status.value = 'uploading'
  message.value = '正在上传并识别，请稍候。'
  try {
    await recordStore.createVoiceDraft(audio)
    uni.navigateTo({ url: '/pages/confirmation/index' })
  } catch (reason) {
    const manual = typeof reason === 'object' && reason !== null
      && 'fallback' in reason && reason.fallback === 'manual_form'
    offerManual(manual
      ? '语音识别暂时不可用，原录音不会直接入账，请改用手动输入。'
      : '语音上传未完成，请重试或改用手动输入。')
  }
}

defineExpose({ submitRecordedAudio })
onMounted(setupRecorder)
onUnmounted(stopTimer)
</script>

<template>
  <main class="page">
    <header><p class="eyebrow">语音记账</p><h1>说清楚，再确认</h1><p>{{ message }}</p></header>
    <section v-if="showDemoAction" class="recorder" aria-label="固定音频演示">
      <span class="permission">{{ permissionText }}</span>
      <button class="primary" type="button" data-action="demo-audio" :disabled="status === 'uploading'" @click="submitDemoAudio">
        {{ status === 'uploading' ? '正在识别…' : '使用固定演示音频' }}
      </button>
    </section>
    <section v-else class="recorder">
      <span class="permission">{{ permissionText }}</span>
      <strong class="duration" aria-label="录音时长">{{ elapsedLabel }}</strong>
      <button type="button" :class="['primary', { 'is-blocked': status === 'blocked' }]" data-action="record-primary" :disabled="status === 'uploading' || status === 'blocked'" @click="handlePrimary">{{ primaryLabel }}</button>
      <button v-if="status === 'recording'" type="button" class="secondary" data-action="pause" @click="pauseRecording">暂停录音</button>
    </section>
    <navigator v-if="showManualFallback" class="manual-fallback" data-action="manual-fallback" url="/pages/record-manual/index" tabindex="0">改用手动输入</navigator>
    <section class="privacy"><h2>录音说明</h2><p>语音只用于生成待确认记录；你点击“确认记账”前不会写入正式账本。</p></section>
  </main>
</template>

<style scoped lang="scss">
@use '../../styles/tokens.scss' as *;
.page{max-width:42rem;margin:auto;padding:$space-4 $space-3 calc($space-5 + env(safe-area-inset-bottom))}
.eyebrow,h1,header p,h2,.privacy p{margin:0}.eyebrow,header p,.privacy p,.permission{color:$muted}
h1{margin:.2rem 0 .35rem;font-size:2rem;letter-spacing:-.04em}
.recorder{display:grid;gap:$space-2;margin:$space-5 0 $space-3;padding:$space-4 0;border-top:1px solid $line;border-bottom:1px solid $line;text-align:center}
.duration{font-variant-numeric:tabular-nums;font-size:3rem;letter-spacing:-.04em}
.primary,.secondary{min-height:$control-height;font-weight:700}.primary{border:0;background:$primary;color:#fff}
.primary:active{background:$primary-pressed}.primary:disabled,.primary.is-blocked{background:#e8ebf0;color:$muted;cursor:not-allowed}
.secondary{border:1px solid $line;background:$surface;color:$ink}
.manual-fallback{display:flex;align-items:center;justify-content:center;min-height:3rem;border:1px solid $primary;border-radius:$radius-small;color:$primary;font-weight:700}
.manual-fallback:focus-visible{outline:3px solid #8cc3ff;outline-offset:2px}
.privacy{margin-top:$space-4;padding-top:$space-3;border-top:1px solid $line}.privacy h2{margin-bottom:.25rem;font-size:1rem}
</style>
