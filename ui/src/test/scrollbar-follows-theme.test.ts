import { describe, expect, it } from 'vitest'

import layoutSource from '../components/Layout.tsx?raw'
import outlineSource from '../components/editor/OutlineSidebar.tsx?raw'
import docCreateSource from '../pages/DocCreate.tsx?raw'
import linksPanelSource from '../components/DocumentLinksPanel.tsx?raw'

/**
 * Scrollbars are painted by the browser, not by Tailwind. The theme lives in a
 * `.dark` class the browser cannot see, so every scrollbar stayed light in dark
 * mode - the main content one worst of all, since it had no styling whatsoever.
 *
 * The `color-scheme` declarations that fix this live in index.css, which Vitest
 * stubs out even through `?raw`; the build asserts those. What is checked here
 * is that no scroll container is left on the unstyled default.
 */

const CONTAINERS: [string, string][] = [
  ['Layout', layoutSource],
  ['OutlineSidebar', outlineSource],
  ['DocCreate', docCreateSource],
  ['DocumentLinksPanel', linksPanelSource],
]

describe.each(CONTAINERS)('%s', (_name, source) => {
  it('themes every scroll container it declares', () => {
    const scrollers = source.match(/className="[^"]*overflow-(?:y-)?auto[^"]*"/g) ?? []
    expect(scrollers.length).toBeGreaterThan(0)
    for (const scroller of scrollers) {
      expect(scroller).toMatch(/themed-scrollbar|sidebar-scrollbar/)
    }
  })
})

describe('main content area', () => {
  it('is the one that had no scrollbar styling at all', () => {
    expect(layoutSource).toMatch(/<main[^>]*overflow-auto themed-scrollbar/)
  })
})
