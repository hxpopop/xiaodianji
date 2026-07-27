import { describe, expect, it } from 'vitest'
import source from '../src/pages/query/index.vue?raw'

describe('query page H5 compatibility', () => {
  it('avoids reactive uni Button slots for query actions', () => {
    expect(source).not.toContain('<button')
    expect(source).toContain('role="button"')
    expect(source).toContain('@keydown.enter="submit(example)"')
  })
})
