import { describe, expect, it } from 'vitest'

import { migrateOldSteps } from '../components/TcsArteTable'

describe('migrateOldSteps', () => {
  it('maps legacy steps into table rows', () => {
    const rows = migrateOldSteps([
      { step_number: 1, action: 'Open page', expected_result: 'Page loads' },
      { step_number: 2, action: 'Submit form', expected_result: 'Success toast' },
    ])

    expect(rows).toHaveLength(2)
    expect(rows[0]).toMatchObject({
      row_type: 'step',
      label: 'Step 1',
      description: 'Open page',
      expected_result: 'Page loads',
      indent_level: 0,
      collapsed: false,
    })
    expect(rows[1].label).toBe('Step 2')
    expect(rows[0].id).toMatch(/^row-/)
  })
})
