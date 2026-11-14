import { renderPage } from './render'
import { describe, expect, it, vi } from 'vitest'

import DocDetailShell from '../components/DocDetailShell'
import { ReviewCommentsContext, type ReviewCommentsState } from '../components/comments/reviewCommentsContext'

vi.mock('react-router', () => ({
  useLocation: () => ({ state: null }),
  useNavigate: () => () => undefined,
}))

describe('DocDetailShell', () => {
  it('shows only the document code and title in the title block', () => {
    const html = renderPage(
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

describe('DocDetailShell information panel', () => {
  it('draws the information panel above the comments beside the content and nothing between the title and the content', () => {
    const html = renderPage(
      <DocDetailShell
        projectPrefix="PRJ"
        docType="REQ"
        docCode="REQ-001"
        title="Brake requirement"
        status="Draft"
        info={<div>Panel contents</div>}
        comments={<div>Comments</div>}
      >
        <div>Body</div>
      </DocDetailShell>,
    )

    expect(html).toContain('aria-label="Document information"')
    expect(html.indexOf('Panel contents')).toBeGreaterThan(html.indexOf('Body'))
    expect(html.indexOf('Panel contents')).toBeLessThan(html.indexOf('Comments'))
    expect(html.indexOf('Body')).toBeGreaterThan(html.indexOf('Brake requirement'))
    expect(html.slice(html.indexOf('Brake requirement'), html.indexOf('Body'))).not.toContain('Document review')
  })

  it('keeps the 380 pixel column for the comments outside a comments provider', () => {
    const html = renderPage(
      <DocDetailShell projectPrefix="PRJ" docType="REQ" docCode="REQ-001" title="Brake requirement" status="Draft" comments={<div>Comments</div>}>
        <div>Body</div>
      </DocDetailShell>,
    )

    expect(html).toContain('lg:grid-cols-[minmax(0,1fr)_380px]')
  })

  it('shrinks the right column to its buttons when the comments are hidden and there is no information panel', () => {
    const html = renderPage(
      <ReviewCommentsContext.Provider value={{ commentsShown: false } as ReviewCommentsState}>
        <DocDetailShell projectPrefix="PRJ" docType="REQ" docCode="REQ-001" title="Brake requirement" status="Draft" comments={<div>Comments</div>}>
          <div>Body</div>
        </DocDetailShell>
      </ReviewCommentsContext.Provider>,
    )

    expect(html).toContain('lg:grid-cols-[minmax(0,1fr)_auto]')
    expect(html).not.toContain('lg:grid-cols-[minmax(0,1fr)_380px]')
  })

  it('keeps the 380 pixel column while the information panel is shown and the comments are hidden', () => {
    const html = renderPage(
      <ReviewCommentsContext.Provider value={{ commentsShown: false } as ReviewCommentsState}>
        <DocDetailShell projectPrefix="PRJ" docType="REQ" docCode="REQ-001" title="Brake requirement" status="Draft" info={<div>Panel contents</div>} comments={<div>Comments</div>}>
          <div>Body</div>
        </DocDetailShell>
      </ReviewCommentsContext.Provider>,
    )

    expect(html).toContain('lg:grid-cols-[minmax(0,1fr)_380px]')
  })

  it('puts the information panel in the side rail when the page has no comments column', () => {
    const html = renderPage(
      <DocDetailShell projectPrefix="PRJ" docType="REQ" docCode="REQ-001" title="Brake requirement" status="Draft" info={<div>Panel contents</div>}>
        <div>Body</div>
      </DocDetailShell>,
    )

    expect(html).toContain('aria-label="Document side panel"')
    expect(html).toContain('Panel contents')
  })
})
