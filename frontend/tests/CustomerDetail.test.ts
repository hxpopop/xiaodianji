import { flushPromises, mount } from '@vue/test-utils'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

const mocks = vi.hoisted(() => ({
  getCustomerBalance: vi.fn(),
  state: { shopId: 'shop-1' },
}))

vi.mock('../src/api/customerBalance', () => ({
  getCustomerBalance: mocks.getCustomerBalance,
}))
vi.mock('../src/stores/record', () => ({
  recordStore: { state: mocks.state },
}))

import CustomerDetail from '../src/pages/customer-detail/index.vue'

describe('customer detail', () => {
  beforeEach(() => {
    mocks.getCustomerBalance.mockResolvedValue({
      customer_id: 'customer-1',
      balance: '128.50',
    })
  })

  afterEach(() => {
    vi.clearAllMocks()
  })

  it('uses the selected customer id for an exact balance lookup', async () => {
    const wrapper = mount(CustomerDetail)
    await (wrapper.vm as unknown as {
      loadCustomer: (name: string, id: string) => Promise<void>
    }).loadCustomer('王老板', 'customer-1')
    await flushPromises()

    expect(mocks.getCustomerBalance).toHaveBeenCalledWith('shop-1', 'customer-1')
    expect(wrapper.text()).toContain('¥128.50')
  })
})
