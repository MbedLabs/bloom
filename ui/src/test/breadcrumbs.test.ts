import { describe, expect, it } from 'vitest'

import { getBreadcrumbs } from '../lib/breadcrumbs'
import { resourceLabel } from '../lib/policySummary'

const projects = [{ id: 1, name: 'Vehicle Control Unit', prefix: 'VCU' }]

describe('getBreadcrumbs', () => {
  it.each([['/access', 'Access'], ['/users', 'Users']])('shows Home and %s', (path, label) => {
    expect(getBreadcrumbs(path, '', projects)).toEqual([{ label: 'Home', href: '/' }, { label }])
  })
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

  it('does not show Edit crumb (sticks to doc list)', () => {
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

describe('collection labels', () => {
  it('names the designs list Designs in the breadcrumbs', () => {
    const crumbs = getBreadcrumbs('/projects/VCU/docs/new', '?type=designs', projects)
    expect(crumbs.map((crumb) => crumb.label)).toContain('Designs')
  })

  it('names the test suites list Test Suites in the breadcrumbs', () => {
    const crumbs = getBreadcrumbs('/projects/VCU/docs/new', '?type=test-suites', projects)
    expect(crumbs[crumbs.length - 1]).toEqual({
      label: 'Test Suites',
      href: '/projects/VCU/docs?type=test-suites',
      emphasize: true,
    })
  })

  it('names a document resource in the policy editor by its collection', () => {
    expect(resourceLabel('DES')).toBe('DES · Designs')
    expect(resourceLabel('CHG')).toBe('CHG · Changes')
    expect(resourceLabel('project')).toBe('Project Management')
  })
})
