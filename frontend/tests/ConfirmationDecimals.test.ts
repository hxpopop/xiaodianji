import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'
import ConfirmationCard from '../src/components/ConfirmationCard.vue'

describe('ConfirmationCard decimal normalization', () => {
  it('renders backend decimal strings without calling toFixed on a string', () => {
    const confirmation = { id: 'c-1', shop_id: 's-1', target_type: 'transaction', status: 'pending', effective_json: { target_type: 'transaction', customer_name: '王老板', occurred_at: '2026-07-27T09:00:00+08:00', payment_status: 'unpaid', items: [{ product: '水泥', quantity: '2.000', unit: '袋', unit_price: '20.00', subtotal: '40.00' }], total_amount: '40.00' }, field_confidences: {}, formal_record_type: null, formal_record_id: null } as any
    const wrapper = mount(ConfirmationCard, { props: { confirmation } })
    expect(wrapper.text()).toContain('¥40.00')
  })
})
