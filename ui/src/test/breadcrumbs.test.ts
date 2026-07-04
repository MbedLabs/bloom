import { describe, expect, it } from 'vitest'

import { getBreadcrumbs } from '../lib/breadcrumbs'

const projects = [{ id: 1, name: 'Vehicle Control Unit', prefix: 'VCU' }]

describe('getBreadcrumbs', () => {
  it('shows doc list label for new doc create, no New X crumb', () => {
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
    ])
    expect(crumbs[crumbs.length - 1]?.href).toBe('/projects/VCU/docs?type=requirements')
    expect(crumbs[crumbs.length - 1]?.emphasize).toBe(true)
  })

  it('shows doc list label for untyped doc create', () => {
    const crumbs = getBreadcrumbs('/projects/VCU/docs/new', '', projects)
    expect(crumbs[crumbs.length - 1]?.label).toBe('Documents')
  })

  it('does not show Edit crumb — sticks to doc list', () => {
    const crumbs = getBreadcrumbs(
      '/projects/VCU/docs/des/VCU-DES-001/edit',
      '?type=des',
      projects,
    )
    expect(crumbs.map((crumb) => crumb.label)).toEqual([
      'Home',
      'Projects',
      'Vehicle Control Unit',
      'Designs',
    ])
    expect(crumbs[crumbs.length - 1]?.href).toBe('/projects/VCU/docs?type=designs')
  })
})
