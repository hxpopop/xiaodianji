import { mount } from '@vue/test-utils'
import { afterEach, describe, expect, it, vi } from 'vitest'

const mocks = vi.hoisted(() => ({
  createVoiceDraft: vi.fn(),
  state: { shopId: 'shop-voice', draft: null, error: '', saving: false },
}))

vi.mock('../src/stores/record', () => ({
  recordStore: {
    state: mocks.state,
    createVoiceDraft: mocks.createVoiceDraft,
  },
}))

import VoiceRecordPage from '../src/pages/record-voice/index.vue'

describe('H5 voice capability detection', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('does not invoke the unsupported recorder shim and offers manual input', async () => {
    const getRecorderManager = vi.fn()
    vi.stubGlobal('uni', {
      getSystemInfoSync: () => ({ uniPlatform: 'web' }),
      getRecorderManager,
      navigateTo: vi.fn(),
    })

    const wrapper = mount(VoiceRecordPage)
    await wrapper.vm.$nextTick()

    expect(getRecorderManager).not.toHaveBeenCalled()
    expect(wrapper.get('[data-action="manual-fallback"]').isVisible()).toBe(true)
    expect(wrapper.text()).toContain('浏览器不支持录音')
  })
})
