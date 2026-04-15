import { useState } from 'react'
import { useParams, Link } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { campaignsApi } from '../api/client'
import { ArrowLeft, PlayCircle, CheckCircle, XCircle, AlertCircle, Clock, SkipForward, MessageSquare } from 'lucide-react'

export default function CampaignDetail() {
  const { id, campaignId } = useParams<{ id: string; campaignId: string }>()
  const projId = parseInt(id || '0')
  const campId = parseInt(campaignId || '0')
  const queryClient = useQueryClient()
  const [commentMap, setCommentMap] = useState<Record<number, string>>({})

  const { data: campaign, isLoading } = useQuery({
    queryKey: ['campaign', campId],
    queryFn: () => campaignsApi.get(campId),
    enabled: !!campId,
  })

  const startMutation = useMutation({
    mutationFn: () => campaignsApi.update(campId, { status: 'In Progress' }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['campaign', campId] }),
  })

  const completeMutation = useMutation({
    mutationFn: () => campaignsApi.update(campId, { status: 'Completed' }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['campaign', campId] }),
  })

  const updateItemMutation = useMutation({
    mutationFn: ({ itemId, data }: { itemId: number; data: { result: string; comment?: string } }) =>
      campaignsApi.updateItem(campId, itemId, data),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['campaign', campId] }),
  })

  const handleSetResult = (itemId: number, result: string) => {
    const comment = commentMap[itemId]
    updateItemMutation.mutate({ itemId, data: { result, comment } })
  }

  if (isLoading) {
    return <div className="flex items-center justify-center h-64 text-muted-foreground">Loading...</div>
  }

  if (!campaign) {
    return (
      <div className="bg-destructive/10 border border-destructive/20 rounded-lg p-6 text-center">
        <h3 className="text-lg font-medium text-destructive">Campaign Not Found</h3>
        <Link to={`/projects/${projId}/campaigns`} className="mt-4 inline-block text-primary hover:text-primary/80">
          &larr; Back to Campaigns
        </Link>
      </div>
    )
  }

  const total = campaign.total_items
  const executed = campaign.passed + campaign.failed + campaign.blocked
  const progress = total > 0 ? (executed / total) * 100 : 0
  const passRate = executed > 0 ? (campaign.passed / executed) * 100 : 0

  return (
    <div className="animate-fade-in space-y-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-4">
          <Link to={`/projects/${projId}/campaigns`} className="p-2 hover:bg-accent/50 rounded-md">
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
        <div className="flex items-center space-x-3">
          {campaign.status === 'Planned' && (
            <button
              onClick={() => startMutation.mutate()}
              disabled={startMutation.isPending}
              className="inline-flex items-center px-4 py-2 bg-primary text-primary-foreground rounded-md hover:bg-primary/90 hover:shadow-glow transition-all duration-200 text-sm font-medium disabled:opacity-50"
            >
              <PlayCircle className="h-4 w-4 mr-2" />
              Start Campaign
            </button>
          )}
          {campaign.status === 'In Progress' && (
            <button
              onClick={() => completeMutation.mutate()}
              disabled={completeMutation.isPending}
              className="inline-flex items-center px-4 py-2 bg-emerald-600 text-white rounded-md hover:bg-emerald-700 transition-colors text-sm font-medium disabled:opacity-50"
            >
              <CheckCircle className="h-4 w-4 mr-2" />
              Complete Campaign
            </button>
          )}
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-5 gap-4">
        <StatCard label="Total" value={total} color="text-foreground" />
        <StatCard label="Passed" value={campaign.passed} color="text-emerald-600" />
        <StatCard label="Failed" value={campaign.failed} color="text-red-600" />
        <StatCard label="Blocked" value={campaign.blocked} color="text-amber-600" />
        <StatCard label="Pass Rate" value={`${Math.round(passRate)}%`} color={passRate >= 80 ? 'text-emerald-600' : passRate >= 50 ? 'text-amber-600' : 'text-red-600'} />
      </div>

      <div className="bg-card rounded-lg shadow-elegant p-5">
        <div className="flex items-center justify-between mb-3">
          <span className="text-sm font-medium text-foreground">Progress</span>
          <span className="text-sm text-muted-foreground">{executed}/{total} executed ({Math.round(progress)}%)</span>
        </div>
        <div className="w-full bg-border rounded-full h-3">
          <div className="h-3 rounded-full flex overflow-hidden">
            {campaign.passed > 0 && (
              <div className="bg-emerald-500 transition-all duration-500" style={{ width: `${total > 0 ? (campaign.passed / total) * 100 : 0}%` }} />
            )}
            {campaign.failed > 0 && (
              <div className="bg-red-500 transition-all duration-500" style={{ width: `${total > 0 ? (campaign.failed / total) * 100 : 0}%` }} />
            )}
            {campaign.blocked > 0 && (
              <div className="bg-amber-500 transition-all duration-500" style={{ width: `${total > 0 ? (campaign.blocked / total) * 100 : 0}%` }} />
            )}
          </div>
        </div>
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

      <div className="bg-card rounded-lg shadow-elegant overflow-hidden">
        <div className="px-6 py-4 border-b border-border">
          <h3 className="text-lg font-semibold">Test Cases</h3>
        </div>
        {!campaign.items || campaign.items.length === 0 ? (
          <div className="p-12 text-center text-muted-foreground">
            No test cases in this campaign.
          </div>
        ) : (
          <div className="divide-y divide-border">
            {campaign.items.map((item) => (
              <div key={item.id} className="px-6 py-4">
                <div className="flex items-center justify-between">
                  <div className="flex items-center space-x-3">
                    <ResultIcon result={item.result} />
                    <div>
                      {item.test_case ? (
                        <Link
                          to={`/test-cases/${item.test_case.id}`}
                          className="font-mono text-sm text-primary hover:text-primary/80 font-medium"
                        >
                          {item.test_case.tc_id}
                        </Link>
                      ) : (
                        <span className="text-sm text-muted-foreground">TC#{item.test_case_id}</span>
                      )}
                      {item.test_case && (
                        <span className="ml-2 text-foreground">{item.test_case.title}</span>
                      )}
                    </div>
                  </div>
                  <div className="flex items-center space-x-2">
                    {item.result && <ResultBadge result={item.result} />}
                    {item.executed_at && (
                      <span className="text-xs text-muted-foreground">
                        {new Date(item.executed_at).toLocaleDateString()}
                      </span>
                    )}
                  </div>
                </div>

                {campaign.status === 'In Progress' && !item.result && (
                  <div className="mt-3 flex items-center space-x-2">
                    <input
                      type="text"
                      placeholder="Add comment..."
                      value={commentMap[item.id] || ''}
                      onChange={(e) => setCommentMap({ ...commentMap, [item.id]: e.target.value })}
                      className="flex-1 px-3 py-1.5 bg-background border border-input rounded-md text-sm focus:ring-2 focus:ring-ring focus:border-ring"
                    />
                    <button
                      onClick={() => handleSetResult(item.id, 'Passed')}
                      className="inline-flex items-center px-3 py-1.5 bg-emerald-500/10 text-emerald-700 dark:text-emerald-400 rounded-md text-xs font-medium hover:bg-emerald-500/20 transition-colors"
                    >
                      <CheckCircle className="h-3.5 w-3.5 mr-1" /> Pass
                    </button>
                    <button
                      onClick={() => handleSetResult(item.id, 'Failed')}
                      className="inline-flex items-center px-3 py-1.5 bg-red-500/10 text-red-700 dark:text-red-400 rounded-md text-xs font-medium hover:bg-red-500/20 transition-colors"
                    >
                      <XCircle className="h-3.5 w-3.5 mr-1" /> Fail
                    </button>
                    <button
                      onClick={() => handleSetResult(item.id, 'Blocked')}
                      className="inline-flex items-center px-3 py-1.5 bg-amber-500/10 text-amber-700 dark:text-amber-400 rounded-md text-xs font-medium hover:bg-amber-500/20 transition-colors"
                    >
                      <AlertCircle className="h-3.5 w-3.5 mr-1" /> Block
                    </button>
                    <button
                      onClick={() => handleSetResult(item.id, 'Skipped')}
                      className="inline-flex items-center px-3 py-1.5 bg-gray-500/10 text-gray-700 dark:text-gray-400 rounded-md text-xs font-medium hover:bg-gray-500/20 transition-colors"
                    >
                      <SkipForward className="h-3.5 w-3.5 mr-1" /> Skip
                    </button>
                  </div>
                )}

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
    'In Progress': { colors: 'bg-blue-500/10 text-blue-700 dark:text-blue-400' },
    Completed: { colors: 'bg-emerald-500/10 text-emerald-700 dark:text-emerald-400' },
    Aborted: { colors: 'bg-red-500/10 text-red-700 dark:text-red-400' },
  }
  const cfg = config[status] || config.Planned
  return (
    <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${cfg.colors}`}>{status}</span>
  )
}

function ResultIcon({ result }: { result: string | null }) {
  if (!result) return <Clock className="h-5 w-5 text-muted-foreground/40" />
  if (result === 'Passed') return <CheckCircle className="h-5 w-5 text-emerald-500" />
  if (result === 'Failed') return <XCircle className="h-5 w-5 text-red-500" />
  if (result === 'Blocked') return <AlertCircle className="h-5 w-5 text-amber-500" />
  return <SkipForward className="h-5 w-5 text-gray-400" />
}

function ResultBadge({ result }: { result: string }) {
  const config: Record<string, string> = {
    Passed: 'bg-emerald-500/10 text-emerald-700 dark:text-emerald-400',
    Failed: 'bg-red-500/10 text-red-700 dark:text-red-400',
    Blocked: 'bg-amber-500/10 text-amber-700 dark:text-amber-400',
    Skipped: 'bg-gray-500/10 text-gray-700 dark:text-gray-400',
  }
  return (
    <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${config[result] || config.Skipped}`}>
      {result}
    </span>
  )
}
