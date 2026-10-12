// @vitest-environment jsdom
import '@testing-library/jest-dom/vitest'
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import UserSelect from '../components/UserSelect'
import { TcsArteTable } from '../components/TcsArteTable'
import { createDefaultTcsRow } from '../utils/tcs'
import ProfilePicture from '../components/ProfilePicture'
import MentionList from '../components/editor/MentionList'
import DocEditor from '../components/editor/DocEditor'
import { authApi, artefactsApi } from '../api/client'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import DocumentActivityPanel from '../components/DocumentActivityPanel'

vi.mock('../api/client', async (original) => {
  const actual = await original<typeof import('../api/client')>()
  return { ...actual, artefactsApi: { ...actual.artefactsApi, listActivity: vi.fn() }, authApi: { ...actual.authApi, fetchProfilePicture: vi.fn() } }
})
const ada = { id: 11, full_name: 'Ada Lovelace', has_profile_picture: true, updated_at: 'one', profile_picture_url: 'data:image/png;base64,YWRh' }
const grace = { id: 12, full_name: 'Grace Hopper', has_profile_picture: true, updated_at: 'one', profile_picture_url: 'data:image/png;base64,Z3JhY2U=' }
const people = [ada, grace].map((user) => ({ id: user.id, label: user.full_name, user }))
afterEach(cleanup)
beforeEach(() => { vi.clearAllMocks(); globalThis.CSS = { ...(globalThis.CSS ?? {}), escape: (value: string) => value } as never })

describe('pictures belong to the displayed user', () => {
  it('renders distinct saved images without fetching the signed-in picture', () => {
    render(<><ProfilePicture user={ada as never} /><ProfilePicture user={grace as never} /></>)
    expect(screen.getByAltText("Ada Lovelace's profile picture")).toHaveAttribute('src', ada.profile_picture_url)
    expect(screen.getByAltText("Grace Hopper's profile picture")).toHaveAttribute('src', grace.profile_picture_url)
    expect(authApi.fetchProfilePicture).not.toHaveBeenCalled()
  })
  it('updates replacement, removal and failed image rendering without losing initials', () => {
    const view = render(<ProfilePicture user={ada as never} />)
    const replacement = { ...ada, profile_picture_url: grace.profile_picture_url }
    view.rerender(<ProfilePicture user={replacement as never} />)
    expect(screen.getByAltText("Ada Lovelace's profile picture")).toHaveAttribute('src', grace.profile_picture_url)
    fireEvent.error(screen.getByAltText("Ada Lovelace's profile picture"))
    expect(screen.getByText('AL')).toBeInTheDocument()
    view.rerender(<ProfilePicture user={{ ...ada, has_profile_picture: false, profile_picture_url: null } as never} />)
    expect(screen.queryByRole('img')).not.toBeInTheDocument()
    expect(screen.getByText('AL')).toBeInTheDocument()
  })
  it('shows each picture in @ suggestions and preserves selection data', () => {
    const command = vi.fn()
    render(<MentionList items={people} command={command} />)
    expect(screen.getByAltText("Ada Lovelace's profile picture")).toHaveAttribute('src', ada.profile_picture_url)
    fireEvent.click(screen.getByRole('button', { name: /@Grace Hopper/ }))
    expect(command).toHaveBeenCalledWith(people[1])
  })
  it('renders a saved @mention using current identity data without serializing the picture', async () => {
    const content = { type: 'doc', content: [{ type: 'paragraph', content: [{ type: 'mention', attrs: { id: ada.id, label: ada.full_name, mentionSuggestionChar: '@' } }] }] }
    const onChange = vi.fn()
    const view = render(<DocEditor content={content} editable={false} userMentionItems={people} onChange={onChange} />)
    expect(await screen.findByAltText("Ada Lovelace's profile picture")).toHaveAttribute('src', ada.profile_picture_url)
    await waitFor(() => expect(onChange).toHaveBeenCalled())
    const [savedJson, savedHtml] = onChange.mock.calls[onChange.mock.calls.length - 1]
    expect(JSON.stringify(savedJson)).toContain('Ada Lovelace')
    expect(JSON.stringify(savedJson)).not.toContain('data:image')
    expect(savedHtml).toContain('@Ada Lovelace')
    expect(savedHtml).not.toContain('<img')
    expect(savedHtml).not.toContain('data:image')
    onChange.mockClear()
    view.rerender(<DocEditor content={content} editable={false} userMentionItems={[{ ...people[0], user: { ...ada, profile_picture_url: grace.profile_picture_url } }]} onChange={onChange} />)
    await waitFor(() => expect(screen.getByAltText("Ada Lovelace's profile picture")).toHaveAttribute('src', grace.profile_picture_url))
    expect(onChange).not.toHaveBeenCalled()
  })
})


describe('picture-aware user choices', () => {
  it('shows pictures for choices and allows keyboard selection and Escape', () => {
    const change = vi.fn()
    render(<UserSelect value="" onChange={change} users={[ada, grace]} label="Reviewer" />)
    const picker = screen.getByRole('combobox', { name: 'Reviewer' })
    fireEvent.keyDown(picker, { key: 'ArrowDown' })
    expect(screen.getByAltText("Ada Lovelace's profile picture")).toHaveAttribute('src', ada.profile_picture_url)
    fireEvent.keyDown(picker, { key: 'ArrowDown' })
    fireEvent.keyDown(picker, { key: 'Enter' })
    expect(change).toHaveBeenCalledWith('12')
    expect(screen.queryByRole('listbox')).not.toBeInTheDocument()
    fireEvent.click(picker)
    fireEvent.keyDown(picker, { key: 'Escape' })
    expect(screen.queryByRole('listbox')).not.toBeInTheDocument()
  })
  it('renders test-step @references without modifying the stored plain strings', () => {
    const row = { ...createDefaultTcsRow('step'), description: 'Notify @Ada Lovelace after the check', expected_result: '@Grace Hopper reads the result' }
    const change = vi.fn()
    render(<TcsArteTable rows={[row]} onChange={change} userMentionItems={people} />)
    expect(screen.getByAltText("Ada Lovelace's profile picture")).toHaveAttribute('src', ada.profile_picture_url)
    expect(screen.getByAltText("Grace Hopper's profile picture")).toHaveAttribute('src', grace.profile_picture_url)
    expect(change).not.toHaveBeenCalled()
    expect(row.description).toBe('Notify @Ada Lovelace after the check')
  })

  it('keeps the keyboard-selected option visible in a long people list', () => {
    const original = HTMLElement.prototype.scrollIntoView
    const scroll = vi.fn()
    HTMLElement.prototype.scrollIntoView = scroll
    try {
      const change = vi.fn()
      const users = Array.from({ length: 30 }, (_, index) => ({ id: index + 1, full_name: `Person ${index + 1}` }))
      render(<UserSelect value="" onChange={change} users={users} label="Reviewer" />)
      const picker = screen.getByRole('combobox', { name: 'Reviewer' })
      fireEvent.keyDown(picker, { key: 'End' })
      const last = screen.getByRole('option', { name: 'Person 30' })
      expect(picker).toHaveAttribute('aria-activedescendant', last.id)
      expect(scroll.mock.contexts[scroll.mock.contexts.length - 1]).toBe(last)
      fireEvent.keyDown(picker, { key: 'Enter' })
      expect(change).toHaveBeenCalledWith('30')
    } finally {
      HTMLElement.prototype.scrollIntoView = original
    }
  })
})


it('renders the identified activity actor without inferring old free-text actors', async () => {
  vi.mocked(artefactsApi.listActivity).mockResolvedValue([
    { id: 1, artefact_type: 'requirement', artefact_id: 1, event_type: 'created', summary: 'Ada created PRJ-REQ-001', actor_user_id: ada.id, actor_name: ada.full_name, actor_profile_picture_url: ada.profile_picture_url, created_at: '2026-10-10T12:00:00Z' },
    { id: 2, artefact_type: 'requirement', artefact_id: 1, event_type: 'updated', summary: 'Unknown updated PRJ-REQ-001', created_at: '2026-10-10T12:01:00Z' },
  ])
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  render(<QueryClientProvider client={client}><DocumentActivityPanel artefactType="requirement" artefactId={1} /></QueryClientProvider>)
  expect(await screen.findByAltText("Ada Lovelace's profile picture")).toHaveAttribute('src', ada.profile_picture_url)
  expect(screen.getByText('Unknown updated PRJ-REQ-001')).toBeInTheDocument()
  expect(screen.getAllByRole('img')).toHaveLength(1)
})
