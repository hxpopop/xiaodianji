import { describe, expect, it } from 'vitest'
import { createApp } from '../src/main'

describe('uni-app bootstrap', () => {
  it('returns the app wrapper required by the uni runtime preset', () => {
    const bootstrap = createApp()

    expect(bootstrap.app).toBeDefined()
    expect(bootstrap.app.use).toEqual(expect.any(Function))
  })
})
