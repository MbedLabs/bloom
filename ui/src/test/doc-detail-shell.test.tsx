import { renderToString } from 'react-dom/server'
import { describe, expect, it, vi } from 'vitest'

import DocDetailShell from '../components/DocDetailShell'

vi.mock('react-router-dom', () => ({
  useLocation: () => ({ state: null }),
  useNavigate: () => () => undefined,
}))

describe('DocDetailShell', () => {
  it('does not duplicate visibility beside the document title', () => {
    const html = renderToString(
      <DocDetailShell
        projectPrefix="PRJ"
        docType="REQ"
        docCode="REQ-001"
        title="Brake requirement"
        status="Draft"
      >
        <div>Body</div>
      </DocDetailShell>,
    )

    expect(html).toContain('Brake requirement')
    expect(html).not.toMatch(/>Internal Only<\/span>/)
    expect(html).not.toMatch(/>Internal<\/span>/)
  })
})
