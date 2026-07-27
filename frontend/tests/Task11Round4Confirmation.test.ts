import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'
import ConfirmationCard from '../src/components/ConfirmationCard.vue'

const confirmation = {
  id: 'confirmation-round-4',
  shop_id: 'shop-1',
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
    source_evidence_id: 'evidence-1',
  },
  field_confidences: {
    customer_name: '0.62',
    occurred_at: '0.62',
    payment_status: '0.62',
    'items.0.product': '0.62',
    'items.0.spec': '0.62',
    'items.0.quantity': '0.62',
    'items.0.unit': '0.62',
    'items.0.unit_price': '0.62',
    'items.0.subtotal': '0.62',
    total_amount: '0.62',
  },
  formal_record_type: null,
  formal_record_id: null,
}

describe('Task 11 round 4 confirmation behavior', () => {
  it('warns in Chinese when a displayed summary field is below the threshold', () => {
    const wrapper = mount(ConfirmationCard, {
      props: { confirmation, confidenceThreshold: 0.75 },
    })

    const customer = wrapper.get('[data-field="customer_name"]')
    expect(customer.classes()).toContain('is-low-confidence')
    expect(customer.text()).toContain('客户识别把握较低，请核对客户')
  })

  it('warns in Chinese when a displayed non-quantity item field is below the threshold', () => {
    const wrapper = mount(ConfirmationCard, {
      props: { confirmation, confidenceThreshold: 0.75 },
    })

    const product = wrapper.get('[data-field="items.0.product"]')
    expect(product.classes()).toContain('is-low-confidence')
    expect(product.text()).toContain('商品识别把握较低，请核对商品')
  })

  it('applies field-specific warnings to every displayed low-confidence field', () => {
    const wrapper = mount(ConfirmationCard, {
      props: { confirmation, confidenceThreshold: 0.75 },
    })
    const expectedWarnings = new Map([
      ['customer_name', '客户识别把握较低，请核对客户'],
      ['occurred_at', '日期识别把握较低，请核对日期'],
      ['payment_status', '付款状态识别把握较低，请核对付款状态'],
      ['items.0.product', '商品识别把握较低，请核对商品'],
      ['items.0.spec', '规格识别把握较低，请核对规格'],
      ['items.0.quantity', '数量识别把握较低，请核对数量'],
      ['items.0.unit', '单位识别把握较低，请核对单位'],
      ['items.0.unit_price', '单价识别把握较低，请核对单价'],
      ['items.0.subtotal', '小计识别把握较低，请核对小计'],
      ['total_amount', '合计识别把握较低，请核对合计'],
    ])

    for (const [field, warning] of expectedWarnings) {
      const element = wrapper.get(`[data-field="${field}"]`)
      expect(element.classes()).toContain('is-low-confidence')
      expect(element.text()).toContain(warning)
    }
  })

  it('submits edits to customer, date, payment, product, spec, unit, and unit price', async () => {
    const wrapper = mount(ConfirmationCard, { props: { confirmation } })

    await wrapper.get('[data-field="customer_name"] input').setValue('李老板')
    await wrapper.get('[data-field="occurred_at"] input').setValue('2026-07-28T10:45')
    await wrapper.get('[data-field="payment_status"] select').setValue('paid')
    await wrapper.get('[data-field="items.0.product"] input').setValue('切割片')
    await wrapper.get('[data-field="items.0.spec"] input').setValue('105mm')
    await wrapper.get('[data-field="items.0.unit"] input').setValue('片')
    await wrapper.get('[data-field="items.0.unit_price"] input').setValue('3.50')
    await wrapper.get('[data-action="confirm"]').trigger('click')

    const payload = wrapper.emitted('confirm')?.[0]?.[0] as {
      edited: boolean
      draft: typeof confirmation.effective_json
    }
    expect(payload.edited).toBe(true)
    expect(payload.draft.customer_name).toBe('李老板')
    expect(payload.draft.occurred_at).toContain('2026-07-28')
    expect(payload.draft.payment_status).toBe('paid')
    expect(payload.draft.items[0]).toMatchObject({
      product: '切割片',
      spec: '105mm',
      unit: '片',
      unit_price: 3.5,
      subtotal: 7,
    })
  })

  it('replaces the edit baseline when the confirmation prop changes', async () => {
    const wrapper = mount(ConfirmationCard, { props: { confirmation } })
    const replacement = {
      ...confirmation,
      id: 'confirmation-replacement',
      effective_json: {
        ...confirmation.effective_json,
        customer_name: '新客户',
      },
    }

    await wrapper.setProps({ confirmation: replacement })
    await wrapper.get('[data-action="confirm"]').trigger('click')

    const payload = wrapper.emitted('confirm')?.[0]?.[0] as { edited: boolean }
    expect(payload.edited).toBe(false)
  })

  it('blocks confirmation and explains invalid quantity and unit price in Chinese', async () => {
    const wrapper = mount(ConfirmationCard, { props: { confirmation } })
    const quantity = wrapper.get('[data-field="items.0.quantity"] input')
    const unitPrice = wrapper.get('[data-field="items.0.unit_price"] input')

    expect(quantity.attributes()).toMatchObject({ min: '0.001', step: '0.001' })
    expect(unitPrice.attributes()).toMatchObject({ min: '0', step: '0.01' })
    await quantity.setValue('0')
    await unitPrice.setValue('-1')
    await wrapper.get('[data-action="confirm"]').trigger('click')

    expect(wrapper.emitted('confirm')).toBeUndefined()
    expect(wrapper.get('[role="alert"]').text()).toContain('数量必须大于 0')
    expect(wrapper.get('[role="alert"]').text()).toContain('单价不能小于 0')
  })

  it('shows typed evidence details and a labeled audio action instead of an opaque id', () => {
    const evidence = {
      id: 'evidence-1',
      type: 'audio',
      status: 'ready',
      original_filename: '王老板语音.m4a',
      mime_type: 'audio/mp4',
      size_bytes: 2048,
      asr_text: '王老板拿了两台角磨机',
      access_url: 'https://objects.example/evidence-1',
    }
    const wrapper = mount(ConfirmationCard, {
      props: { confirmation, evidence, evidenceState: 'ready' } as any,
    })

    expect(wrapper.text()).toContain('语音凭证')
    expect(wrapper.text()).toContain('王老板语音.m4a')
    expect(wrapper.text()).toContain('转写内容：王老板拿了两台角磨机')
    const action = wrapper.get('[data-action="open-evidence"]')
    expect(action.text()).toContain('播放原始音频')
    expect(wrapper.text()).not.toContain('凭证编号：evidence-1')
  })

  it('emits an image URL from a labeled button instead of using a navigator', async () => {
    const evidence = {
      id: 'evidence-image',
      type: 'image',
      status: 'ready',
      original_filename: '送货单.jpg',
      mime_type: 'image/jpeg',
      size_bytes: 4096,
      asr_text: null,
      access_url: 'https://objects.example/evidence-image',
    }
    const wrapper = mount(ConfirmationCard, {
      props: { confirmation, evidence, evidenceState: 'ready' } as any,
    })

    const action = wrapper.get('[data-action="open-evidence"]')
    expect(action.element.tagName).toBe('BUTTON')
    expect(action.text()).toContain('查看原始图片')
    expect(wrapper.find('navigator[data-action="open-evidence"]').exists()).toBe(false)

    await action.trigger('click')
    expect(wrapper.emitted('open-evidence')).toEqual([[
      { type: 'image', url: 'https://objects.example/evidence-image' },
    ]])
  })

  it.each([
    ['loading', '正在加载原始凭证…'],
    ['missing', '本次没有关联原始凭证。'],
    ['unavailable', '原始凭证暂时无法查看，请稍后重试。'],
  ] as const)('shows the %s evidence state in Chinese', (evidenceState, message) => {
    const wrapper = mount(ConfirmationCard, {
      props: { confirmation, evidence: null, evidenceState } as any,
    })

    expect(wrapper.text()).toContain(message)
  })
})
