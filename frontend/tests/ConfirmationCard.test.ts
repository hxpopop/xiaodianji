import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'
import ConfirmationCard from '../src/components/ConfirmationCard.vue'

const confirmation = {
  id: 'confirmation-1', shop_id: 'shop-1', target_type: 'transaction' as const, status: 'pending' as const,
  effective_json: { target_type: 'transaction' as const, customer_name: '王老板', occurred_at: '2026-07-27T09:30:00+08:00', payment_status: 'unpaid' as const,
    items: [{ product: '水泥', quantity: 5, unit: '袋', unit_price: 20, subtotal: 100 }, { product: '砂纸', quantity: 2, unit: '包', unit_price: 10, subtotal: 20 }], total_amount: 120, source_evidence_id: 'evidence-1' },
  field_confidences: { 'items.1.quantity': '0.62' }, formal_record_type: null, formal_record_id: null,
}

describe('ConfirmationCard', () => {
  it('marks a quantity below the confidence threshold for review', () => {
    const wrapper = mount(ConfirmationCard, { props: { confirmation, confidenceThreshold: 0.75 } })
    expect(wrapper.get('[data-field="items.1.quantity"]').classes()).toContain('is-low-confidence')
  })

  it('emits an edited draft when the quantity is changed before confirmation', async () => {
    const wrapper = mount(ConfirmationCard, { props: { confirmation } })
    await wrapper.get('[data-field="items.0.quantity"] input').setValue('10')
    await wrapper.get('[data-action="confirm"]').trigger('click')
    const payload = wrapper.emitted('confirm')?.[0]?.[0] as { edited: boolean; draft: typeof confirmation.effective_json }
    expect(payload.edited).toBe(true)
    expect(payload.draft.items[0].quantity).toBe(10)
  })
})
