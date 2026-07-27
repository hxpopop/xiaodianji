import { flushPromises, mount } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'

const mocks = vi.hoisted(() => {
  const confirmation = {
    id: 'confirmation-evidence',
    shop_id: 'shop-evidence',
    target_type: 'transaction' as const,
    status: 'pending' as const,
    effective_json: {
      target_type: 'transaction' as const,
      customer_name: '王老板',
      occurred_at: '2026-07-27T09:30:00+08:00',
      payment_status: 'unpaid' as const,
      items: [{
        product: '角磨机',
        spec: '100型',
        quantity: 2,
        unit: '台',
        unit_price: 280,
        subtotal: 560,
      }],
      total_amount: 560,
      source_evidence_id: 'evidence-typed',
    },
    field_confidences: {},
    formal_record_type: null,
    formal_record_id: null,
  }
  return {
    confirmation,
    getEvidence: vi.fn(),
    state: {
      shopId: 'shop-evidence',
      draft: confirmation,
      error: '',
      saving: false,
    },
  }
})

vi.mock('../src/api/client', () => ({
  apiClient: { getEvidence: mocks.getEvidence },
}))

vi.mock('../src/stores/record', () => ({
  recordStore: {
    state: mocks.state,
    resolveDraft: vi.fn(),
    cancelDraft: vi.fn(),
  },
}))

import ConfirmationPage from '../src/pages/confirmation/index.vue'

describe('Task 11 round 4 evidence loading', () => {
  beforeEach(() => {
    mocks.getEvidence.mockReset()
    mocks.getEvidence.mockResolvedValue({
      id: 'evidence-typed',
      type: 'audio',
      status: 'ready',
      original_filename: '原始语音.m4a',
      mime_type: 'audio/mp4',
      size_bytes: 4096,
      asr_text: '王老板拿了两台角磨机',
      access_url: 'https://objects.example/evidence-typed',
    })
  })

  it('loads typed evidence with the current shop and evidence id', async () => {
    const wrapper = mount(ConfirmationPage)
    await flushPromises()

    expect(mocks.getEvidence).toHaveBeenCalledWith('shop-evidence', 'evidence-typed')
    expect(wrapper.text()).toContain('原始语音.m4a')
    expect(wrapper.text()).toContain('王老板拿了两台角磨机')
  })
})
