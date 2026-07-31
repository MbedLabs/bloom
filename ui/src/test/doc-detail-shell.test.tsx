import { renderToString } from 'react-dom/server'
import { describe, expect, it, vi } from 'vitest'

import DocDetailShell from '../components/DocDetailShell'

vi.mock('react-router', () => ({
  useLocation: () => ({ state: null }),
  useNavigate: () => () => undefined,
}))

describe('DocDetailShell', () => {
  it('shows only the document code and title in the title block', () => {
    const html = renderToString(
      <DocDetailShell
        projectPrefix="PRJ"
        docType="REQ"
        docCode="REQ-001"
        title="Brake requirement"
        status="Draft"
        priority="High"
      >
        <div>Body</div>
      </DocDetailShell>,
    )

    expect(html).toContain('REQ-001')
    expect(html).toContain('Brake requirement')
    expect(html).not.toMatch(/>Requirement<\/span>/)
    expect(html).not.toMatch(/>Draft<\/span>/)
    expect(html).not.toMatch(/>High<\/span>/)
    expect(html).not.toMatch(/>Internal Only<\/span>/)
    expect(html).not.toMatch(/>Internal<\/span>/)
  })
})
