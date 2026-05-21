import { describe, expect, it } from 'vitest'

import type { User } from '../api/client'
import { docRegistryListUrl } from '../lib/docRegistryParams'

describe('OSS readiness smoke', () => {
  it('User role contract includes external (not reviewer)', () => {
    const u: User = {
      id: 1,
      email: 'u@example.com',
      full_name: 'User',
      role: 'external',
      is_active: true,
      created_at: '',
      updated_at: '',
    }
    expect(u.role).toBe('external')
  })

  it('doc registry list URL encodes requirement type', () => {
    const url = docRegistryListUrl('VCU', 'REQ')
    expect(url).toContain('/projects/VCU/docs')
    expect(url).toContain('type=requirements')
  })
})
