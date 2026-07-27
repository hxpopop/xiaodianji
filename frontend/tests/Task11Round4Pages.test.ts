import { flushPromises, mount } from '@vue/test-utils'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import HomePage from '../src/pages/index/index.vue'
import TextRecordPage from '../src/pages/record-text/index.vue'

describe('Task 11 round 4 page behavior', () => {
  const navigateTo = vi.fn()

  beforeEach(() => {
    vi.stubGlobal('uni', { navigateTo, reLaunch: vi.fn() })
  })

  afterEach(() => {
    vi.unstubAllGlobals()
    vi.clearAllMocks()
  })

  it('keeps voice dominant and reports unavailable actions without misleading routes', async () => {
    const wrapper = mount(HomePage)
    await flushPromises()

    expect(wrapper.get('h1').text()).toBe('小店记')
    expect(wrapper.get('[data-action="voice"]').text()).toContain('说一笔')
    await wrapper.get('[data-action="voice"]').trigger('click')
    expect(wrapper.text()).toContain('语音记账即将开放')
    expect(navigateTo).not.toHaveBeenCalled()

    await wrapper.get('[data-action="query"]').trigger('click')
    expect(wrapper.text()).toContain('查欠款功能即将开放')
    expect(navigateTo).not.toHaveBeenCalled()
  })

  it('keeps text, manual, and query actions visible while routing only implemented pages', async () => {
    const wrapper = mount(HomePage)
    await flushPromises()

    expect(wrapper.get('[data-action="text"]').text()).toContain('文字记账')
    expect(wrapper.get('[data-action="manual"]').text()).toContain('手动输入')
    expect(wrapper.get('[data-action="query"]').text()).toContain('查欠款')
    await wrapper.get('[data-action="text"]').trigger('click')
    await wrapper.get('[data-action="manual"]').trigger('click')
    expect(navigateTo.mock.calls).toEqual([
      [{ url: '/pages/record-text/index' }],
      [{ url: '/pages/record-manual/index' }],
    ])
  })

  it('exposes the manual fallback as a named keyboard-focusable target', () => {
    const wrapper = mount(TextRecordPage)
    const fallback = wrapper.get('[data-action="manual-fallback"]')

    expect(fallback.attributes('aria-label')).toBe('改用手动输入')
    expect(fallback.classes()).toContain('manual-fallback')
  })
})
