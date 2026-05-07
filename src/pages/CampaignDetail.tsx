import { useParams, Link } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { campaignsApi } from '../api/client'
import { ArrowLeft, Clock, MessageSquare } from 'lucide-react'
import { docUrl } from '../types/doc'

export default function CampaignDetail() {
  const { prefix, campaignId } = useParams<{ prefix: string; campaignId: string }>()
  const campId = parseInt(campaignId || '0')

  const { data: campaign, isLoading } = useQuery({
    queryKey: ['campaign', campId],
    queryFn: () => campaignsApi.get(campId),
    enabled: !!campId,
  })

  if (isLoading) {
    return <div className="flex items-center justify-center h-64 text-muted-foreground">Loading...</div>
  }

  if (!campaign) {
    return (
      <div className="bg-destructive/10 border border-destructive/20 rounded-lg p-6 text-center">
        <h3 className="text-lg font-medium text-destructive">Campaign Not Found</h3>
        <Link to={`/projects/${prefix}/campaigns`} className="mt-4 inline-block text-primary hover:text-primary/80">
          &larr; Back to Campaigns
        </Link>
      </div>
    )
  }

  const total = campaign.total_items

  return (
    <div className="animate-fade-in space-y-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-4">
          <Link to={`/projects/${prefix}/campaigns`} className="p-2 hover:bg-accent/50 rounded-md">
            <ArrowLeft className="h-5 w-5 text-muted-foreground" />
          </Link>
          <div>
            <div className="flex items-center space-x-3">
              <h2 className="text-2xl font-bold text-foreground">{campaign.name}</h2>
              <CampaignStatusBadge status={campaign.status} />
            </div>
            {campaign.description && <p className="text-muted-foreground mt-0.5">{campaign.description}</p>}
          </div>
        </div>
        <div />
      </div>

      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <StatCard label="Total" value={total} color="text-foreground" />
        <StatCard label="Scope Items" value={total} color="text-primary" />
        <StatCard label="Bud Run" value={campaign.bud_run_id || '-'} color="text-foreground" />
        <StatCard label="Req Coverage" value={campaign.related_requirements?.length || 0} color="text-emerald-600" />
      </div>

      <div className="bg-card rounded-lg shadow-elegant p-5">
        <div className="flex items-center justify-between mb-3">
          <span className="text-sm font-medium text-foreground">Bud Execution Link</span>
          {campaign.bud_run_status && <span className="px-2 py-1 rounded-full text-xs font-medium bg-muted text-muted-foreground">{campaign.bud_run_status}</span>}
        </div>
        {campaign.bud_run_url ? (
          <a href={campaign.bud_run_url} target="_blank" rel="noopener noreferrer" className="inline-flex items-center px-3 py-2 rounded-md bg-primary text-white hover:bg-primary/90 text-sm">
            Open in Bud
          </a>
        ) : (
          <div className="text-sm text-muted-foreground">No Bud run linked yet. Bloom stores traceability scope; execution is owned by Bud.</div>
        )}
      </div>

      {campaign.configuration && (
        <div className="bg-card rounded-lg shadow-elegant p-5">
          <h3 className="text-sm font-medium text-muted-foreground mb-2">Configuration</h3>
          <div className="flex items-center space-x-4 text-sm">
            <span className="text-foreground font-medium">{campaign.configuration.name}</span>
            {campaign.configuration.environment && (
              <span className="px-2 py-0.5 bg-muted rounded text-xs text-muted-foreground">{campaign.configuration.environment}</span>
            )}
          </div>
        </div>
      )}

      {campaign.suite && (
        <div className="bg-card rounded-lg shadow-elegant p-5">
          <h3 className="text-sm font-medium text-muted-foreground mb-2">Source Suite</h3>
          <div className="flex items-center justify-between gap-4">
            <div>
              <div className="font-mono text-sm text-primary">{campaign.suite.suite_id}</div>
              <div className="text-foreground mt-1">{campaign.suite.name}</div>
            </div>
            <span className="px-2 py-1 rounded-full text-xs font-medium bg-muted text-muted-foreground">{campaign.suite.status}</span>
          </div>
        </div>
      )}

      <div className="bg-card rounded-lg shadow-elegant p-5">
        <h3 className="text-sm font-medium text-muted-foreground mb-3">Requirement Coverage</h3>
        {campaign.related_requirements && campaign.related_requirements.length > 0 ? (
          <div className="flex flex-wrap gap-2">
            {campaign.related_requirements.map((req) => (
              <Link key={req.id} to={docUrl(prefix!, 'REQ', req.req_id)} className="inline-flex items-center px-3 py-2 rounded-md bg-primary/10 text-primary hover:bg-primary/15 text-sm">
                <span className="font-mono mr-2">{req.req_id}</span>
                {req.title}
              </Link>
            ))}
          </div>
        ) : (
          <p className="text-sm text-muted-foreground">No requirements are covered by this campaign scope yet.</p>
        )}
      </div>

      <div className="bg-card rounded-lg shadow-elegant overflow-hidden">
        <div className="px-6 py-4 border-b border-border">
          <h3 className="text-lg font-semibold">Test Cases In Scope</h3>
        </div>
        {!campaign.items || campaign.items.length === 0 ? (
          <div className="p-12 text-center text-muted-foreground">No test cases in this campaign scope.</div>
        ) : (
          <div className="divide-y divide-border">
            {campaign.items.map((item) => (
              <div key={item.id} className="px-6 py-4">
                <div className="flex items-center justify-between">
                  <div className="flex items-center space-x-3">
                    <Clock className="h-5 w-5 text-primary/60" />
                    <div>
                      {item.test_case ? (
                        <Link to={docUrl(prefix!, 'TC', item.test_case.tc_id)} className="font-mono text-sm text-primary hover:text-primary/80 font-medium">
                          {item.test_case.tc_id}
                        </Link>
                      ) : (
                        <span className="text-sm text-muted-foreground">TC#{item.test_case_id}</span>
                      )}
                      {item.test_case && <span className="ml-2 text-foreground">{item.test_case.title}</span>}
                      {item.test_case?.linked_requirements && item.test_case.linked_requirements.length > 0 && (
                        <div className="mt-2 flex flex-wrap gap-2">
                          {item.test_case.linked_requirements.map((req) => (
                            <Link key={req.id} to={docUrl(prefix!, 'REQ', req.req_id)} className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-primary/10 text-primary hover:bg-primary/15">
                              <span className="font-mono mr-1">{req.req_id}</span>
                              {req.title}
                            </Link>
                          ))}
                        </div>
                      )}
                    </div>
                  </div>
                  <div className="flex items-center space-x-2">
                    <ResultBadge result={item.result || item.status || 'Pending'} />
                    {item.result && item.status && (
                      <span className="text-xs text-muted-foreground">{item.status}</span>
                    )}
                  </div>
                </div>

                {item.comment && (
                  <div className="mt-2 flex items-start space-x-2 text-sm">
                    <MessageSquare className="h-3.5 w-3.5 text-muted-foreground mt-0.5 flex-shrink-0" />
                    <span className="text-muted-foreground">{item.comment}</span>
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}

function StatCard({ label, value, color }: { label: string; value: number | string; color: string }) {
  return (
    <div className="bg-card rounded-lg shadow-elegant p-4">
      <p className="text-sm text-muted-foreground">{label}</p>
      <p className={`text-2xl font-bold ${color}`}>{value}</p>
    </div>
  )
}

function CampaignStatusBadge({ status }: { status: string }) {
  const config: Record<string, { colors: string }> = {
    Planned: { colors: 'bg-gray-500/10 text-gray-700 dark:text-gray-400' },
    Scope: { colors: 'bg-blue-500/10 text-blue-700 dark:text-blue-400' },
    Completed: { colors: 'bg-emerald-500/10 text-emerald-700 dark:text-emerald-400' },
    Aborted: { colors: 'bg-red-500/10 text-red-700 dark:text-red-400' },
  }
  const cfg = config[status] || config.Planned
  return <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${cfg.colors}`}>{status}</span>
}

function ResultBadge({ result }: { result: string }) {
  const config: Record<string, string> = {
    Passed: 'bg-emerald-500/10 text-emerald-700 dark:text-emerald-400',
    Failed: 'bg-red-500/10 text-red-700 dark:text-red-400',
    Skipped: 'bg-slate-500/10 text-slate-700 dark:text-slate-400',
    Planned: 'bg-blue-500/10 text-blue-700 dark:text-blue-400',
    Scope: 'bg-blue-500/10 text-blue-700 dark:text-blue-400',
    Pending: 'bg-gray-500/10 text-gray-700 dark:text-gray-400',
    Linked: 'bg-cyan-500/10 text-cyan-700 dark:text-cyan-400',
    Executed: 'bg-slate-500/10 text-slate-700 dark:text-slate-400',
  }
  return (
    <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${config[result] || config.Pending}`}>
      {result}
    </span>
  )
}
