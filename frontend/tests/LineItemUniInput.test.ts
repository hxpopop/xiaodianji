import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'
import LineItemEditor from '../src/components/LineItemEditor.vue'

describe('LineItemEditor uni input events', () => {
  it('reads the cross-platform detail.value payload', async () => {
    const wrapper = mount(LineItemEditor, {
      props: {
        index: 1,
        item: { product: '电线', quantity: 2, unit: '卷', unit_price: 150, subtotal: 300 },
      },
    })
    await wrapper.get('[data-field="items.1.quantity"] input').trigger('input', {
      detail: { value: '3' },
    })
    expect(wrapper.emitted('update:item')?.[0]?.[0]).toMatchObject({ quantity: 3 })
  })
})
