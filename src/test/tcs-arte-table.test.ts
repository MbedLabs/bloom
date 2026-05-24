import { createElement } from 'react'
import { renderToStaticMarkup } from 'react-dom/server'
import { describe, expect, it } from 'vitest'

import { TcsArteTable } from '../components/TcsArteTable'
import { migrateOldSteps, normalizeTcsRows } from '../utils/tcs'

describe('migrateOldSteps', () => {
  it('maps legacy steps into table rows without numbered labels', () => {
    const rows = migrateOldSteps([
      { step_number: 1, action: 'Open page', expected_result: 'Page loads' },
      { step_number: 2, action: 'Submit form', expected_result: 'Success toast' },
    ])

    expect(rows).toHaveLength(2)
    expect(rows[0]).toMatchObject({
      row_type: 'step',
      label: 'Step',
      description: 'Open page',
      expected_result: 'Page loads',
      indent_level: 0,
      collapsed: false,
    })
    expect(rows[1].label).toBe('Step')
    expect(rows[0].id).toMatch(/^row-/)
  })
})

describe('normalizeTcsRows', () => {
  it('preserves structured TCS rows without forcing generated labels', () => {
    const rows = normalizeTcsRows([
      {
        id: 'stored-1',
        row_type: 'loop',
        label: 'Loop',
        description: '',
        expected_result: '',
        indent_level: 1,
        collapsed: true,
      },
    ])

    expect(rows[0]).toMatchObject({
      id: 'stored-1',
      row_type: 'loop',
      label: 'Loop',
      indent_level: 1,
      collapsed: true,
    })
  })
})

describe('TcsArteTable', () => {
  it('shows the real row type in the Type column even when stored labels contain sentences', () => {
    const html = renderToStaticMarkup(
      createElement(TcsArteTable, {
        editable: false,
        onChange: () => {},
        rows: [
          {
            id: 'stored-1',
            row_type: 'step',
            label: 'Verify severity counts match actual counts',
            description: 'Count info, warning, and critical violations in the list.',
            expected_result: 'The summary severity counts each equal the actual count.',
            indent_level: 0,
            collapsed: false,
          },
        ],
      }),
    )

    expect(html).toContain('Step')
    expect(html).not.toContain('Verify severity counts match actual counts')
  })
})
