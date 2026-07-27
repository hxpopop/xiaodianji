import { mount } from '@vue/test-utils'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

const mocks = vi.hoisted(() => ({
  createVoiceDraft: vi.fn(),
  state: {
    shopId: 'shop-voice',
    draft: null,
    error: '',
    saving: false,
  },
}))

vi.mock('../src/stores/record', () => ({
  recordStore: {
    state: mocks.state,
    createVoiceDraft: mocks.createVoiceDraft,
  },
}))

import VoiceRecordPage from '../src/pages/record-voice/index.vue'

describe('voice recording fallback', () => {
  beforeEach(() => {
    vi.stubGlobal('uni', {
      getRecorderManager: () => ({
        onStop: vi.fn(),
        onError: vi.fn(),
        start: vi.fn(),
        pause: vi.fn(),
        resume: vi.fn(),
        stop: vi.fn(),
      }),
      navigateTo: vi.fn(),
    })
    mocks.createVoiceDraft.mockReset()
  })

  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('shows manual form action when ASR fails', async () => {
    mocks.createVoiceDraft.mockRejectedValue({ fallback: 'manual_form' })
    const wrapper = mount(VoiceRecordPage)
    const demoBlob = new Blob(['voice'], { type: 'audio/mpeg' })

    expect(wrapper.find('[data-action="manual-fallback"]').exists()).toBe(false)
    await (wrapper.vm as unknown as {
      submitRecordedAudio: (audio: Blob) => Promise<void>
    }).submitRecordedAudio(demoBlob)

    expect(wrapper.get('[data-action="manual-fallback"]').isVisible()).toBe(true)
    expect(wrapper.text()).toContain('改用手动输入')
  })
})
