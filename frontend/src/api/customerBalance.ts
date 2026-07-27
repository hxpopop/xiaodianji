export interface CustomerBalanceRead {
  customer_id: string
  balance: string | number
}

const baseUrl = (import.meta.env.VITE_API_BASE_URL || '/api/v1').replace(/\/$/, '')

export async function getCustomerBalance(
  shopId: string,
  customerId: string,
): Promise<CustomerBalanceRead> {
  if (!shopId) {
    throw new Error('尚未配置商户，请联系管理员设置商户信息后再记账。')
  }
  const response = await fetch(
    `${baseUrl}/customers/${encodeURIComponent(customerId)}/balance`,
    {
      headers: {
        Accept: 'application/json',
        'X-Shop-Id': shopId,
      },
    },
  )
  if (!response.ok) throw new Error('客户账目暂时无法加载。')
  return response.json() as Promise<CustomerBalanceRead>
}
