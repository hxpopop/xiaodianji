import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'
import QueryResult from '../src/components/QueryResult.vue'

const demoBalanceResult = {
  answer: '当前欠款为 220.00 元。',
  amount: '220.00',
  calculation_basis: '赊账交易总额 - 收款总额',
  details: [
    {
      id: 'transaction-1',
      type: 'transaction',
      occurred_at: '2026-07-20T09:30:00+08:00',
      amount: '300.00',
      evidence_id: 'evidence-1',
    },
    {
      id: 'payment-1',
      type: 'payment',
      paid_at: '2026-07-21T10:00:00+08:00',
      amount: '80.00',
      evidence_id: null,
    },
  ],
  evidence_ids: ['evidence-1'],
  ambiguity: null,
}

describe('QueryResult', () => {
  it('renders amount, calculation basis, details and evidence action', () => {
    const wrapper = mount(QueryResult, { props: { result: demoBalanceResult } })

    expect(wrapper.text()).toContain('220.00')
    expect(wrapper.text()).toContain('赊账交易总额 - 收款总额')
    expect(wrapper.text()).toContain('交易')
    expect(wrapper.text()).toContain('收款')
    expect(wrapper.find('[data-action="open-evidence"]').exists()).toBe(true)
  })

  it('emits the real evidence id from a labeled action', async () => {
    const wrapper = mount(QueryResult, { props: { result: demoBalanceResult } })

    await wrapper.get('[data-action="open-evidence"]').trigger('click')

    expect(wrapper.emitted('open-evidence')).toEqual([['evidence-1']])
    expect(wrapper.get('[data-action="open-evidence"]').text()).toContain('查看凭证')
  })
})
