<script setup lang="ts">
import { ref, watch } from 'vue'
import { apiClient } from '../../api/client'
import type { EvidenceRead, RecordDraft } from '../../api/types'
import ConfirmationCard from '../../components/ConfirmationCard.vue'
import { recordStore } from '../../stores/record'

type EvidenceState = 'loading' | 'ready' | 'missing' | 'unavailable'
type ImageEvidenceOpen = { type: 'image'; url: string }

const threshold = Number(import.meta.env.VITE_CONFIDENCE_THRESHOLD || .75)
const evidence = ref<EvidenceRead | null>(null)
const evidenceState = ref<EvidenceState>('missing')
let evidenceRequest = 0

watch(
  () => [
    recordStore.state.shopId,
    recordStore.state.draft?.effective_json.source_evidence_id ?? null,
  ] as const,
  async ([shopId, evidenceId]) => {
    const request = ++evidenceRequest
    evidence.value = null
    if (!evidenceId) {
      evidenceState.value = 'missing'
      return
    }
    evidenceState.value = 'loading'
    try {
      const loaded = await apiClient.getEvidence(shopId, evidenceId)
      if (request !== evidenceRequest) return
      evidence.value = loaded
      evidenceState.value = 'ready'
    } catch {
      if (request !== evidenceRequest) return
      evidenceState.value = 'unavailable'
    }
  },
  { immediate: true },
)


function openEvidence(payload: ImageEvidenceOpen) {
  uni.previewImage({
    current: payload.url,
    urls: [payload.url],
  })
}
async function confirm(payload: { draft: RecordDraft; edited: boolean }) {
  try {
    await recordStore.resolveDraft(payload.draft, payload.edited)
    uni.reLaunch({ url: '/pages/index/index' })
  } catch {
    // The store exposes an actionable Chinese error below the card.
  }
}

async function cancel() {
  try {
    await recordStore.cancelDraft()
    uni.reLaunch({ url: '/pages/index/index' })
  } catch {
    // The store exposes an actionable Chinese error below the card.
  }
}
</script>

<template>
  <main>
    <ConfirmationCard
      v-if="recordStore.state.draft"
      :confirmation="recordStore.state.draft"
      :confidence-threshold="threshold"
      :evidence="evidence"
      :evidence-state="evidenceState"
      @confirm="confirm"
      @open-evidence="openEvidence"
      @cancel="cancel"
    />
    <section v-else class="empty">
      <h1>没有待确认的记录</h1>
      <navigator url="/pages/record-manual/index">去手动输入</navigator>
    </section>
    <section v-if="recordStore.state.error" class="error" role="alert">
      <p>{{ recordStore.state.error }}</p>
      <navigator url="/pages/record-manual/index">改用手动输入</navigator>
    </section>
  </main>
</template>

<style scoped lang="scss">
@use '../../styles/tokens.scss' as *;

.empty,
.error {
  padding: $space-4 $space-3 calc($space-4 + env(safe-area-inset-bottom));
}

.error {
  color: $danger;
}

.error navigator,
.empty navigator {
  display: inline-flex;
  align-items: center;
  min-height: $control-height;
  color: $primary;
  font-weight: 700;
}
</style>
