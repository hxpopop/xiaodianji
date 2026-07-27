import { mount } from '@vue/test-utils'
import { afterEach, expect, it, vi } from 'vitest'

vi.mock('../src/stores/record', () => ({
  recordStore: {
    state: { shopId: 'shop-voice', draft: null, error: '', saving: false },
    createVoiceDraft: vi.fn(),
  },
}))

import VoiceRecordPage from '../src/pages/record-voice/index.vue'

afterEach(() => {
  vi.unstubAllGlobals()
})

it('labels the H5 recorder control as honestly unavailable', async () => {
  vi.stubGlobal('uni', {
    getSystemInfoSync: () => ({ uniPlatform: 'web' }),
    getRecorderManager: vi.fn(),
    navigateTo: vi.fn(),
  })
  const wrapper = mount(VoiceRecordPage)
  await wrapper.vm.$nextTick()

  const primary = wrapper.get('[data-action="record-primary"]')
  expect(primary.attributes('disabled')).toBeDefined()
  expect(primary.text()).toBe('录音不可用')
  expect(primary.classes()).toContain('is-blocked')
})
