import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'
import ConfirmationCard from '../src/components/ConfirmationCard.vue'

const confirmation = {
  id: 'confirmation-text-evidence',
  shop_id: 'shop-1',
  target_type: 'transaction' as const,
  status: 'pending' as const,
  effective_json: {
    target_type: 'transaction' as const,
    customer_name: '王老板',
    occurred_at: '2026-07-27T09:30:00+08:00',
    payment_status: 'unpaid' as const,
    items: [{ product: '角磨机', quantity: 2, unit: '台', unit_price: 280, subtotal: 560 }],
    total_amount: 560,
    source_evidence_id: 'evidence-text',
  },
  field_confidences: {},
  formal_record_type: null,
  formal_record_id: null,
}

describe('confirmation text evidence action', () => {
  it('routes a remote text evidence through the real evidence page action', async () => {
    const evidence = {
      id: 'evidence-text',
      type: 'text' as const,
      status: 'ready',
      original_filename: '原始记录.txt',
      mime_type: 'text/plain',
      size_bytes: 42,
      asr_text: '王老板拿了两台角磨机',
      access_url: 'https://objects.example/evidence-text',
    }
    const wrapper = mount(ConfirmationCard, {
      props: { confirmation, evidence, evidenceState: 'ready' },
    })

    const action = wrapper.get('[data-action="open-evidence"]')
    expect(action.element.tagName).toBe('BUTTON')
    expect(action.text()).toContain('查看原始文本')
    expect(wrapper.find('navigator[data-action="open-evidence"]').exists()).toBe(false)

    await action.trigger('click')
    expect(wrapper.emitted('open-evidence')).toEqual([[
      { type: 'text', evidenceId: 'evidence-text' },
    ]])
  })
})
