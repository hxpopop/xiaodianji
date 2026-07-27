import { describe, expect, it } from 'vitest'
import source from '../src/pages/record-voice/index.vue?raw'

describe('voice demo mode', () => {
  it('submits signed demo audio through the real voice workflow', () => {
    expect(source).toContain('VITE_DEMO_MODE')
    expect(source).toContain('data-action="demo-audio"')
    expect(source).toContain("new Blob(['ID3xiaodianji-demo-audio']")
    expect(source).toContain("type: 'audio/mpeg'")
  })
})
