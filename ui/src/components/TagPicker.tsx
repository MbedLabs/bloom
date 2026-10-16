import { useEffect, useMemo } from 'react'
import { useQuery } from '@tanstack/react-query'
import { tagsApi } from '../api/client'

export default function TagPicker({
  projectId,
  value,
  onChange,
  showLabel = true,
}: Readonly<{
  projectId: number
  value: number[]
  onChange: (tagIds: number[]) => void
  showLabel?: boolean
}>) {
  const { data } = useQuery({
    queryKey: ['tag-scope', projectId],
    queryFn: () => tagsApi.scope(projectId),
    enabled: !!projectId,
  })
  const tags = useMemo(() => data?.tags ?? [], [data])
  const limited = data?.limited === true

  useEffect(() => {
    if (limited && tags.length === 1 && value.length === 0) onChange([tags[0].id])
  }, [limited, tags, value.length, onChange])

  if (tags.length === 0) return null
  return (
    <div>
      {showLabel && <span className="block text-sm font-medium text-foreground mb-1">
        Origin{limited ? ' (choose at least one)' : ''}
      </span>}
      <div className="flex flex-wrap gap-1.5" aria-label="Custom origins">
        {tags.map((tag) => (
          <button
            type="button"
            key={tag.id}
            onClick={() => onChange(value.includes(tag.id) ? value.filter((x) => x !== tag.id) : [...value, tag.id])}
            className={
              'px-2 py-0.5 rounded-full text-xs border ' +
              (value.includes(tag.id)
                ? 'bg-primary text-white border-primary'
                : 'bg-background text-muted-foreground border-input')
            }
          >
            {tag.name}
          </button>
        ))}
      </div>
    </div>
  )
}
