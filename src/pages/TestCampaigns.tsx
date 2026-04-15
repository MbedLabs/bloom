import { useState } from 'react'
import { useParams, Link } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { campaignsApi, testCasesApi } from '../api/client'
import { ArrowLeft, Plus, PlayCircle, CheckCircle, XCircle, AlertCircle, Clock, FlaskConical } from 'lucide-react'

export default function TestCampaigns() {
  const { id } = useParams<{ id: string }>()
  const projectId = parseInt(id || '0')
  const queryClient = useQueryClient()
  const [showCreate, setShowCreate] = useState(false)
  const [form, setForm] = useState({ name: '', description: '' })
  const [selectedTcIds, setSelectedTcIds] = useState<number[]>([])

  const { data: campaigns, isLoading } = useQuery({
    queryKey: ['campaigns', projectId],
    queryFn: () => campaignsApi.list(projectId),
    enabled: !!projectId,
  })

  const { data: testCases } = useQuery({
    queryKey: ['projectTestCases', projectId],
    queryFn: () => testCasesApi.list(projectId),
    enabled: !!projectId && showCreate,
  })

  const createMutation = useMutation({
    mutationFn: campaignsApi.create,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['campaigns', projectId] })
      setShowCreate(false)
      setForm({ name: '', description: '' })
      setSelectedTcIds([])
    },
  })

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    createMutation.mutate({
      project_id: projectId,
      name: form.name,
      description: form.description || undefined,
      test_case_ids: selectedTcIds,
    })
  }

  const toggleTc = (tcId: number) => {
    setSelectedTcIds(prev =>
      prev.includes(tcId) ? prev.filter(id => id !== tcId) : [...prev, tcId]
    )
  }

  if (isLoading) {
    return <div className="flex items-center justify-center h-64 text-muted-foreground">Loading...</div>
  }

  return (
    <div className="animate-fade-in space-y-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-4">
          <Link to={`/projects/${projectId}`} className="p-2 hover:bg-accent/50 rounded-md">
            <ArrowLeft className="h-5 w-5 text-muted-foreground" />
          </Link>
          <div>
            <h2 className="text-2xl font-bold text-foreground">Test Campaigns</h2>
            <p className="text-muted-foreground">Execute test cases in organized campaigns</p>
          </div>
        </div>
        <button
          onClick={() => setShowCreate(true)}
          className="inline-flex items-center px-4 py-2 bg-primary text-primary-foreground rounded-md hover:bg-primary/90 hover:shadow-glow transition-all duration-200 text-sm font-medium"
        >
          <Plus className="h-4 w-4 mr-2" />
          New Campaign
        </button>
      </div>

      {!campaigns || campaigns.length === 0 ? (
        <div className="bg-card rounded-lg shadow-elegant p-12 text-center">
          <div className="w-16 h-16 rounded-2xl bg-gradient-to-br from-primary/10 to-cyan-500/10 flex items-center justify-center mx-auto mb-4">
            <FlaskConical className="h-8 w-8 text-primary/40" />
          </div>
          <h3 className="text-lg font-medium text-foreground mb-2">No Test Campaigns</h3>
          <p className="text-muted-foreground max-w-md mx-auto mb-5">
            Create a test campaign to organize and execute test cases with specific configurations.
          </p>
          <button
            onClick={() => setShowCreate(true)}
            className="inline-flex items-center px-4 py-2 bg-primary text-primary-foreground rounded-md hover:bg-primary/90 transition-colors text-sm font-medium"
          >
            <Plus className="h-4 w-4 mr-2" />
            Create First Campaign
          </button>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {campaigns.map((campaign) => (
            <CampaignCard key={campaign.id} campaign={campaign} projectId={projectId} />
          ))}
        </div>
      )}

      {showCreate && (
        <div className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-50">
          <div className="bg-card rounded-lg shadow-elegant max-w-lg w-full mx-4 max-h-[80vh] flex flex-col">
            <div className="px-6 py-4 border-b border-border">
              <h3 className="text-lg font-semibold">New Test Campaign</h3>
            </div>
            <form onSubmit={handleSubmit} className="flex flex-col flex-1 overflow-hidden">
              <div className="p-6 space-y-4 overflow-y-auto">
                <div>
                  <label className="block text-sm font-medium text-foreground mb-1">Name</label>
                  <input
                    type="text"
                    required
                    value={form.name}
                    onChange={(e) => setForm({ ...form, name: e.target.value })}
                    className="w-full px-3 py-2 bg-background border border-input rounded-md focus:ring-2 focus:ring-ring focus:border-ring"
                    placeholder="Campaign name"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-foreground mb-1">Description</label>
                  <textarea
                    value={form.description}
                    onChange={(e) => setForm({ ...form, description: e.target.value })}
                    className="w-full px-3 py-2 bg-background border border-input rounded-md focus:ring-2 focus:ring-ring focus:border-ring"
                    rows={2}
                    placeholder="Optional description..."
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-foreground mb-1">
                    Select Test Cases ({selectedTcIds.length} selected)
                  </label>
                  <div className="border border-input rounded-md max-h-48 overflow-y-auto">
                    {testCases && testCases.length > 0 ? (
                      testCases.map((tc) => (
                        <label
                          key={tc.id}
                          className="flex items-center px-3 py-2 hover:bg-accent/30 cursor-pointer border-b border-border last:border-b-0"
                        >
                          <input
                            type="checkbox"
                            checked={selectedTcIds.includes(tc.id)}
                            onChange={() => toggleTc(tc.id)}
                            className="mr-3 accent-primary"
                          />
                          <span className="font-mono text-xs text-primary mr-2">{tc.tc_id}</span>
                          <span className="text-sm text-foreground truncate">{tc.title}</span>
                        </label>
                      ))
                    ) : (
                      <div className="p-4 text-center text-sm text-muted-foreground">
                        No test cases available. Create test cases first.
                      </div>
                    )}
                  </div>
                </div>
              </div>
              <div className="px-6 py-4 border-t border-border flex justify-end space-x-3">
                <button
                  type="button"
                  onClick={() => { setShowCreate(false); setSelectedTcIds([]) }}
                  className="px-4 py-2 border border-input rounded-md text-foreground hover:bg-accent/50"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={createMutation.isPending}
                  className="px-4 py-2 bg-primary text-white rounded-md hover:bg-primary/90 disabled:opacity-50"
                >
                  {createMutation.isPending ? 'Creating...' : 'Create Campaign'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  )
}

function CampaignCard({ campaign, projectId }: { campaign: import('../api/client').TestCampaign; projectId: number }) {
  const total = campaign.total_items
  const progress = total > 0 ? ((campaign.passed + campaign.failed + campaign.blocked) / total) * 100 : 0

  return (
    <Link
      to={`/projects/${projectId}/campaigns/${campaign.id}`}
      className="bg-card rounded-lg shadow-elegant p-5 hover:shadow-glow hover:border-primary/20 border border-transparent transition-all duration-200 group"
    >
      <div className="flex items-start justify-between mb-3">
        <div>
          <h3 className="font-semibold text-foreground group-hover:text-primary transition-colors">{campaign.name}</h3>
          {campaign.description && (
            <p className="text-sm text-muted-foreground mt-0.5 line-clamp-1">{campaign.description}</p>
          )}
        </div>
        <CampaignStatusBadge status={campaign.status} />
      </div>

      {campaign.configuration && (
        <div className="mb-3 text-xs text-muted-foreground">
          Config: <span className="text-foreground font-medium">{campaign.configuration.name}</span>
          {campaign.configuration.environment && (
            <span className="ml-1">({campaign.configuration.environment})</span>
          )}
        </div>
      )}

      {total > 0 && (
        <div>
          <div className="flex items-center justify-between mb-1.5">
            <div className="flex items-center space-x-3 text-xs">
              <span className="flex items-center text-emerald-600"><CheckCircle className="h-3 w-3 mr-1" />{campaign.passed}</span>
              <span className="flex items-center text-red-600"><XCircle className="h-3 w-3 mr-1" />{campaign.failed}</span>
              <span className="flex items-center text-amber-600"><AlertCircle className="h-3 w-3 mr-1" />{campaign.blocked}</span>
              <span className="flex items-center text-muted-foreground"><Clock className="h-3 w-3 mr-1" />{campaign.pending}</span>
            </div>
            <span className="text-xs text-muted-foreground">{Math.round(progress)}%</span>
          </div>
          <div className="w-full bg-border rounded-full h-1.5">
            <div className="h-1.5 rounded-full bg-gradient-to-r from-primary to-cyan-500 transition-all duration-500" style={{ width: `${progress}%` }} />
          </div>
        </div>
      )}

      {total === 0 && (
        <p className="text-xs text-muted-foreground">No test cases added yet</p>
      )}
    </Link>
  )
}

function CampaignStatusBadge({ status }: { status: string }) {
  const config: Record<string, { colors: string; icon: React.ComponentType<{ className?: string }> }> = {
    Planned: { colors: 'bg-gray-500/10 text-gray-700 dark:text-gray-400', icon: Clock },
    'In Progress': { colors: 'bg-blue-500/10 text-blue-700 dark:text-blue-400', icon: PlayCircle },
    Completed: { colors: 'bg-emerald-500/10 text-emerald-700 dark:text-emerald-400', icon: CheckCircle },
    Aborted: { colors: 'bg-red-500/10 text-red-700 dark:text-red-400', icon: XCircle },
  }
  const cfg = config[status] || config.Planned
  const Icon = cfg.icon
  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${cfg.colors}`}>
      <Icon className="h-3 w-3 mr-1" />
      {status}
    </span>
  )
}
