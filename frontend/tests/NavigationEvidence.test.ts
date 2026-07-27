import { flushPromises, mount } from '@vue/test-utils'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

const mocks = vi.hoisted(() => ({
  getEvidence: vi.fn(),
  state: {
    shopId: 'shop-evidence',
  },
}))

vi.mock('../src/api/client', () => ({
  apiClient: {
    getEvidence: mocks.getEvidence,
  },
}))

vi.mock('../src/stores/record', () => ({
  recordStore: {
    state: mocks.state,
  },
}))

import BottomNavigation from '../src/components/BottomNavigation.vue'
import EvidencePage from '../src/pages/evidence/index.vue'

describe('bottom navigation route semantics', () => {
  const reLaunch = vi.fn()

  beforeEach(() => {
    vi.stubGlobal('uni', { reLaunch })
  })

  afterEach(() => {
    vi.unstubAllGlobals()
    vi.clearAllMocks()
  })

  it('marks the current destination and routes implemented destinations', async () => {
    const wrapper = mount(BottomNavigation, { props: { active: 'query' } })

    expect(wrapper.get('[data-nav="query"]').attributes('aria-current')).toBe('page')
    expect(wrapper.get('[data-nav="query"]').attributes('disabled')).toBeDefined()
    await wrapper.get('[data-nav="customers"]').trigger('click')

    expect(reLaunch).toHaveBeenCalledWith({ url: '/pages/customers/index' })
  })
})

describe('text evidence remote action', () => {
  const open = vi.fn()

  beforeEach(() => {
    vi.stubGlobal('uni', {
      previewImage: vi.fn(),
      downloadFile: vi.fn(),
      openDocument: vi.fn(),
    })
    vi.spyOn(window, 'open').mockImplementation(open)
    mocks.getEvidence.mockResolvedValue({
      id: 'evidence-text',
      type: 'text',
      status: 'ready',
      original_filename: '原始记录.txt',
      mime_type: 'text/plain',
      size_bytes: 42,
      asr_text: '王老板拿了两台角磨机',
      access_url: 'https://objects.example/evidence-text',
    })
  })

  afterEach(() => {
    vi.restoreAllMocks()
    vi.unstubAllGlobals()
  })

  it('shows text content and opens the remote URL without a local navigator', async () => {
    const wrapper = mount(EvidencePage)

    await (wrapper.vm as unknown as {
      loadEvidence: (id: string) => Promise<void>
    }).loadEvidence('evidence-text')
    await flushPromises()
    expect(wrapper.text()).toContain('王老板拿了两台角磨机')
    expect(wrapper.find('navigator[data-action="open-remote"]').exists()).toBe(false)

    await wrapper.get('[data-action="open-remote"]').trigger('click')

    expect(open).toHaveBeenCalledWith(
      'https://objects.example/evidence-text',
      '_blank',
      'noopener,noreferrer',
    )
  })
})
