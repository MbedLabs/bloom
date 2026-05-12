import { describe, expect, it } from 'vitest'

import { getBreadcrumbs } from '../lib/breadcrumbs'

const projects = [{ id: 1, name: 'Vehicle Control Unit', prefix: 'VCU' }]

describe('getBreadcrumbs', () => {
  it('labels typed doc create with list and New Requirement', () => {
    const crumbs = getBreadcrumbs(
      '/projects/VCU/docs/new',
      '?type=requirements',
      projects,
    )
    expect(crumbs.map((crumb) => crumb.label)).toEqual([
      'Home',
      'Projects',
      'Vehicle Control Unit',
      'Requirements',
      'New Requirement',
    ])
    expect(crumbs[crumbs.length - 2]?.href).toBe('/projects/VCU/docs?type=requirements')
    expect(crumbs[crumbs.length - 1]?.href).toBeUndefined()
    expect(crumbs[crumbs.length - 2]?.emphasize).toBe(true)
    expect(crumbs[crumbs.length - 1]?.emphasize).toBe(true)
  })

  it('labels untyped doc create as New document', () => {
    const crumbs = getBreadcrumbs('/projects/VCU/docs/new', '', projects)
    expect(crumbs[crumbs.length - 1]?.label).toBe('New document')
  })
})
