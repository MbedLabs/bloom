import { describe, expect, it } from 'vitest'

const sources = import.meta.glob('../{pages,components}/*.tsx', {
  eager: true,
  query: '?raw',
  import: 'default',
}) as Record<string, string>

/**
 * Every save and delete says whether it worked.
 *
 * Six detail pages each carried their own copy of a toast. Everything else
 * reported nothing, or an inline banner that could be scrolled out of view: the
 * document editor flipped its button to "Saved" for two seconds and, on delete,
 * simply navigated away - indistinguishable from a misclick. Adding or removing
 * a relationship, creating a baseline, editing a project parameter and inviting
 * a user all failed silently.
 *
 * This walks the real mutation call sites rather than a hand-kept list, so a new
 * one cannot quietly skip its feedback.
 */

/** Files whose mutations are not user-initiated saves. */
const EXEMPT = new Set([
  // Long-running import with its own progress and result screens.
  'ImportWizard.tsx',
  // Sign-out and the command palette: navigation, not persistence.
  'Layout.tsx',
])

interface Site {
  file: string
  body: string
}

function mutationSites(): Site[] {
  const sites: Site[] = []
  for (const [path, source] of Object.entries(sources)) {
    const file = path.split('/').pop()!
    if (EXEMPT.has(file)) continue
    // Each useMutation({...}) block up to the line that closes it.
    const pattern = /useMutation\(\{[\s\S]*?\n {2}\}\)/g
    for (const match of source.match(pattern) ?? []) {
      sites.push({ file, body: match })
    }
  }
  return sites
}

const SITES = mutationSites()

describe('mutation inventory', () => {
  it('finds the app mutations', () => {
    // Guards the regexes above: if this collapses, the suite silently passes.
    expect(SITES.length).toBeGreaterThan(30)
  })
})

describe('every mutation reports failure', () => {
  it.each(SITES.map((s, i) => [`${s.file} #${i}`, s] as const))('%s', (_label, site) => {
    expect(site.body).toMatch(/onError/)
  })
})

describe('every mutation reports success', () => {
  it.each(SITES.map((s, i) => [`${s.file} #${i}`, s] as const))('%s', (_label, site) => {
    expect(site.body).toMatch(/onSuccess/)
  })
})

describe('feedback is the shared toast', () => {
  const usingToast = Object.entries(sources).filter(([, source]) =>
    source.includes('useMutation('),
  )

  it.each(
    usingToast
      .filter(([path]) => !EXEMPT.has(path.split('/').pop()!))
      .map(([path, source]) => [path.split('/').pop()!, source] as const),
  )('%s uses useToast rather than a private copy', (_file, source) => {
    expect(source).toContain('useToast')
    // The six hand-rolled copies this replaced.
    expect(source).not.toContain('setToast(')
  })
})

describe('the document editor', () => {
  const docCreate = sources['../pages/DocCreate.tsx']

  it('confirms a save', () => {
    expect(docCreate).toContain('toast.saved(')
  })

  it('confirms a delete instead of just navigating away', () => {
    expect(docCreate).toContain('toast.deleted(')
  })

  it('reports why a save or delete failed', () => {
    expect(docCreate.match(/toast\.failed\(/g) ?? []).toHaveLength(2)
  })
})
