import { describe, expect, it } from 'vitest'

const sources = import.meta.glob(['../{pages,components}/*.tsx', '../hooks/*.ts'], {
  eager: true,
  query: '?raw',
  import: 'default',
}) as Record<string, string>

/** Files whose mutations are not user-initiated saves. */
const EXEMPT = new Set([
  'ImportWizard.tsx',
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
    expect(source).not.toContain('setToast(')
  })
})

describe('failure messages read as sentences', () => {
  const callSites = Object.entries(sources).flatMap(([path, source]) =>
    (source.match(/toast\.failed\(\s*[`'"][^`'"]*[`'"]/g) ?? []).map(
      (call) => [path.split('/').pop()!, call] as const,
    ),
  )

  it('finds the failure call sites', () => {
    expect(callSites.length).toBeGreaterThan(20)
  })

  it.each(callSites)('%s: %s', (_file, call) => {
    expect(call.toLowerCase()).not.toContain('failed,')
    expect(call.toLowerCase()).not.toMatch(/fail(ed|ure)?[`'"]$/)
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
