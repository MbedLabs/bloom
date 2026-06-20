import { useQuery } from '@tanstack/react-query'

import { artefactsApi } from '../api/client'
import { formatDateTime } from '../test/date-utils'
import { SectionCard } from './DocDetailShell'

export default function DocumentActivityPanel({
  artefactType,
  artefactId,
  title = 'Activity',
}: {
  artefactType: string
  artefactId: number
  title?: string
}) {
  const { data: activity } = useQuery({
    queryKey: ['artefactActivity', artefactType, artefactId],
    queryFn: () => artefactsApi.listActivity(artefactType, artefactId),
    enabled: artefactId > 0,
  })

  return (
    <SectionCard title={`${title} (${activity?.length ?? 0})`}>
      {!activity || activity.length === 0 ? (
        <p className="text-muted-foreground">No activity recorded yet.</p>
      ) : (
        <div className="space-y-4">
          {activity.map((event) => (
            <div key={event.id} className="flex gap-4">
              <div className="mt-1 h-2.5 w-2.5 rounded-full bg-primary shrink-0" />
              <div>
                <div className="font-medium text-foreground">{event.summary}</div>
                <div className="text-xs text-muted-foreground mt-1">
                  {event.event_type} · {formatDateTime(event.created_at)} ago
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </SectionCard>
  )
}
