import { refreshProjectViews } from '../lib/refreshProjectViews'
import { useState, type ReactNode } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { artefactTagsApi, tagsApi, type TaggedArtefactType } from '../api/client'
import { useAuth } from '../contexts/AuthContext'
import { useToast } from './useToast'

export default function ArtefactTags({
  type,
  id,
  projectId,
  canEdit,
  origin,
}: Readonly<{
  type: TaggedArtefactType
  id: number
  projectId: number
  canEdit: boolean
  origin?: ReactNode
}>) {
  const toast = useToast()
  const { user } = useAuth()
  const queryClient = useQueryClient()
  const key = ['artefact-tags', type, id]
  const carriedQuery = useQuery({ queryKey: key, queryFn: () => artefactTagsApi.get(type, id) })
  const [editing, setEditing] = useState(false)
  const [chosen, setChosen] = useState<number[]>([])
  const offeredQuery = useQuery({
    queryKey: ['tags', projectId],
    queryFn: () => tagsApi.list(projectId),
    enabled: canEdit && user?.role !== 'external',
  })
  const save = useMutation({
    mutationFn: () => artefactTagsApi.set(type, id, chosen),
    onSuccess: (tags) => {
      refreshProjectViews(queryClient, { projectId })
      queryClient.setQueryData(key, tags)
      setEditing(false)
      toast.saved('Origin')
    },
    onError: (error) => toast.failed('Saving the origin', error),
  })
  const carried = carriedQuery.data ?? []
  const offered = offeredQuery.data ?? []
  const mayEdit = canEdit && user?.role !== 'external'

  if (!origin && carried.length === 0 && offered.length === 0 && !carriedQuery.isError && !offeredQuery.isError) return null
  return (
    <div className="flex flex-wrap items-center gap-1.5 text-sm" aria-label="Origin">
      {origin}
      {carriedQuery.isError && <span role="alert">Could not load origins.</span>}
      {editing ? (
        <>
          {offeredQuery.isError && <span role="alert">Could not load origin choices.</span>}
          {offered.map((tag) => (
            <button
              type="button"
              key={tag.id}
              onClick={() =>
                setChosen((prev) => (prev.includes(tag.id) ? prev.filter((x) => x !== tag.id) : [...prev, tag.id]))
              }
              className={
                'px-2 py-0.5 rounded-full text-xs border ' +
                (chosen.includes(tag.id)
                  ? 'bg-primary text-white border-primary'
                  : 'bg-background text-muted-foreground border-input')
              }
            >
              {tag.name}
            </button>
          ))}
          <button
            type="button"
            onClick={() => save.mutate()}
            disabled={save.isPending}
            className="text-xs px-2 py-0.5 rounded bg-primary text-white disabled:opacity-50"
          >
            Save origins
          </button>
          <button type="button" onClick={() => setEditing(false)} className="text-xs px-2 py-0.5 rounded border border-input">
            Cancel
          </button>
        </>
      ) : (
        <>
          {carried.map((tag) => (
            <span key={tag.id} className="px-2 py-0.5 rounded-full border border-border text-xs text-foreground">
              {tag.name}
            </span>
          ))}
          {mayEdit && (carried.length > 0 || offered.length > 0) && (
            <button
              type="button"
              onClick={() => {
                setChosen(carried.map((tag) => tag.id))
                setEditing(true)
              }}
              className="text-xs text-muted-foreground hover:text-foreground underline"
            >
              Edit origins
            </button>
          )}
        </>
      )}
    </div>
  )
}
