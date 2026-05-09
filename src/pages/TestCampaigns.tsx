import { useState } from 'react'
import { useParams, Link } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { campaignsApi, extractApiErrorMessage, testCasesApi, testSuitesApi } from '../api/client'
import { ArrowLeft, Plus, Clock, FlaskConical, Layers3 } from 'lucide-react'
import { useProjectByPrefix } from '../hooks/useProjectByPrefix'

export default function TestCampaigns() {
  const { prefix } = useParams<{ prefix: string }>()
  const { data: project } = useProjectByPrefix(prefix)
  const projectId = project?.id || 0
  const queryClient = useQueryClient()
  const [showCreate, setShowCreate] = useState(false)
  const [showCreateSuite, setShowCreateSuite] = useState(false)
  const [form, setForm] = useState({ name: '', description: '' })
  const [suiteForm, setSuiteForm] = useState({ name: '', description: '' })
  const [selectedTcIds, setSelectedTcIds] = useState<number[]>([])
  const [selectedSuiteIds, setSelectedSuiteIds] = useState<number[]>([])
  const [createError, setCreateError] = useState('')

  const { data: campaigns, isLoading } = useQuery({
    queryKey: ['campaigns', projectId],
    queryFn: () => campaignsApi.list(projectId),
    enabled: !!projectId,
  })

  const { data: suites } = useQuery({
    queryKey: ['testSuites', projectId],
    queryFn: () => testSuitesApi.list(projectId),
    enabled: !!projectId,
  })

  const { data: testCases } = useQuery({
    queryKey: ['projectTestCases', projectId],
    queryFn: () => testCasesApi.list(projectId),
    enabled: !!projectId && showCreateSuite,
  })

  const hasSuites = (suites?.length || 0) > 0

  const openCreateCampaign = () => {
    setCreateError('')
    setSelectedTcIds([])
    setSelectedSuiteIds([])
    setShowCreate(true)
  }

  const createMutation = useMutation({
    mutationFn: campaignsApi.create,
    onMutate: () => {
      setCreateError('')
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['campaigns', projectId] })
      setShowCreate(false)
      setForm({ name: '', description: '' })
      setSelectedTcIds([])
      setSelectedSuiteIds([])
    },
    onError: (error: unknown) => {
      setCreateError(extractApiErrorMessage(error, 'Campaign creation failed.'))
    },
  })

  const createSuiteMutation = useMutation({
    mutationFn: testSuitesApi.create,
    onSuccess: (suite) => {
      queryClient.invalidateQueries({ queryKey: ['testSuites', projectId] })
      queryClient.invalidateQueries({ queryKey: ['project', projectId] })
      setShowCreateSuite(false)
      setSuiteForm({ name: '', description: '' })
      setSelectedTcIds([])
      setSelectedSuiteIds((prev) => [...prev, suite.id])
    },
  })

  const toggleSuiteId = (id: number) => {
    setSelectedSuiteIds((prev) =>
      prev.includes(id) ? prev.filter((s) => s !== id) : [...prev, id]
    )
  }

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (selectedSuiteIds.length === 0) {
      setCreateError('Select at least one suite before creating a campaign.')
      return
    }
    createMutation.mutate({
      project_id: projectId,
      name: form.name,
      description: form.description || undefined,
      suite_ids: selectedSuiteIds,
    })
  }

  const handleSuiteSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    createSuiteMutation.mutate({
      project_id: projectId,
      name: suiteForm.name,
      description: suiteForm.description || undefined,
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
          <Link to={`/projects/${prefix}`} className="p-2 hover:bg-accent/50 rounded-md">
            <ArrowLeft className="h-5 w-5 text-muted-foreground" />
          </Link>
          <div>
            <h2 className="text-2xl font-bold text-foreground">Test Campaigns</h2>
            <p className="text-muted-foreground">Traceability scopes mapped to Bud execution runs</p>
          </div>
        </div>
        <div className="flex items-center gap-3">
          <button
            onClick={() => setShowCreateSuite(true)}
            className="inline-flex items-center px-4 py-2 border border-input text-foreground rounded-md hover:bg-accent/50 transition-all duration-200 text-sm font-medium"
          >
            <Layers3 className="h-4 w-4 mr-2" />
            New Suite
          </button>
          <button
            onClick={openCreateCampaign}
            className="inline-flex items-center px-4 py-2 bg-primary text-primary-foreground rounded-md hover:bg-primary/90 hover:shadow-glow transition-all duration-200 text-sm font-medium"
          >
            <Plus className="h-4 w-4 mr-2" />
            New Campaign
          </button>
        </div>
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-[420px_1fr] gap-6">
        <div className="bg-card rounded-lg shadow-elegant overflow-hidden">
          <div className="px-6 py-4 border-b border-border flex items-center justify-between">
            <div>
              <h3 className="text-lg font-semibold text-foreground">Suites</h3>
              <p className="text-sm text-muted-foreground mt-1">Reusable collections of test cases.</p>
            </div>
            <span className="text-sm text-muted-foreground">{suites?.length || 0}</span>
          </div>
          {!suites || suites.length === 0 ? (
            <div className="p-8 text-center text-muted-foreground">No suites defined yet.</div>
          ) : (
            <div className="divide-y divide-border">
              {suites.map((suite) => (
                <Link key={suite.id} to={`/projects/${prefix}/suites/${suite.id}`} className="block px-6 py-4 hover:bg-accent/40">
                  <div className="flex items-center justify-between gap-4">
                    <div>
                      <div className="font-mono text-xs text-primary">{suite.suite_id}</div>
                      <div className="font-medium text-foreground mt-1">{suite.name}</div>
                      {suite.description && <div className="text-sm text-muted-foreground mt-1">{suite.description}</div>}
                    </div>
                    <div className="text-right">
                      <span className="px-2 py-1 rounded-full text-xs font-medium bg-muted text-muted-foreground">{suite.status}</span>
                      <div className="text-xs text-muted-foreground mt-2">{suite.total_items} TC{suite.total_items !== 1 ? 's' : ''}</div>
                    </div>
                  </div>
                </Link>
              ))}
            </div>
          )}
        </div>

        <div>
          {!campaigns || campaigns.length === 0 ? (
            <div className="bg-card rounded-lg shadow-elegant p-12 text-center">
              <div className="w-16 h-16 rounded-2xl bg-gradient-to-br from-primary/10 to-cyan-500/10 flex items-center justify-center mx-auto mb-4">
                <FlaskConical className="h-8 w-8 text-primary/40" />
              </div>
              <h3 className="text-lg font-medium text-foreground mb-2">No Campaign Scopes</h3>
              <p className="text-muted-foreground max-w-md mx-auto mb-5">
                Build a campaign scope from a test suite, then link the Bud run.
              </p>
              <button
                onClick={openCreateCampaign}
                className="inline-flex items-center px-4 py-2 bg-primary text-primary-foreground rounded-md hover:bg-primary/90 transition-colors text-sm font-medium"
              >
                <Plus className="h-4 w-4 mr-2" />
                Create First Campaign
              </button>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {campaigns.map((campaign) => (
                <CampaignCard key={campaign.id} campaign={campaign} prefix={prefix!} />
              ))}
            </div>
          )}
        </div>
      </div>

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
                    Campaign Suites ({selectedSuiteIds.length} selected)
                  </label>
                  <div className="border border-input rounded-md max-h-48 overflow-y-auto">
                    {(suites || []).length > 0 ? (
                      (suites || []).map((suite) => (
                        <label key={suite.id} className="flex items-center px-3 py-2 hover:bg-accent/30 cursor-pointer border-b border-border last:border-b-0">
                          <input
                            type="checkbox"
                            checked={selectedSuiteIds.includes(suite.id)}
                            onChange={() => toggleSuiteId(suite.id)}
                            className="mr-3 accent-primary"
                          />
                          <span className="font-mono text-xs text-primary mr-2">{suite.suite_id}</span>
                          <span className="text-sm text-foreground truncate">{suite.name}</span>
                          <span className="ml-auto text-xs text-muted-foreground">{suite.total_items} TC{suite.total_items !== 1 ? 's' : ''}</span>
                        </label>
                      ))
                    ) : (
                      <div className="p-4 text-center text-sm text-muted-foreground">No suites available.</div>
                    )}
                  </div>
                  {!hasSuites && (
                    <div className="mt-2 rounded-md border border-amber-500/30 bg-amber-500/10 px-3 py-2 text-sm text-amber-700 dark:text-amber-300">
                      Create a test suite first. Campaigns are scoped from suites.
                    </div>
                  )}
                  {createError && (
                    <div className="mt-2 rounded-md border border-destructive/30 bg-destructive/10 px-3 py-2 text-sm text-destructive">
                      {createError}
                    </div>
                  )}
                  <p className="mt-2 text-xs text-muted-foreground">
                    Campaign items are copied from the selected suites at creation time.
                  </p>
                </div>
              </div>
              <div className="px-6 py-4 border-t border-border flex justify-end space-x-3">
                <button
                  type="button"
                  onClick={() => { setShowCreate(false); setCreateError(''); setSelectedTcIds([]); setSelectedSuiteIds([]) }}
                  className="px-4 py-2 border border-input rounded-md text-foreground hover:bg-accent/50"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={createMutation.isPending || selectedSuiteIds.length === 0}
                  className="px-4 py-2 bg-primary text-white rounded-md hover:bg-primary/90 disabled:opacity-50"
                >
                  {createMutation.isPending ? 'Creating...' : 'Create Campaign'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {showCreateSuite && (
        <div className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-50">
          <div className="bg-card rounded-lg shadow-elegant max-w-lg w-full mx-4 max-h-[80vh] flex flex-col">
            <div className="px-6 py-4 border-b border-border">
              <h3 className="text-lg font-semibold">New Test Suite</h3>
            </div>
            <form onSubmit={handleSuiteSubmit} className="flex flex-col flex-1 overflow-hidden">
              <div className="p-6 space-y-4 overflow-y-auto">
                <div>
                  <label className="block text-sm font-medium text-foreground mb-1">Name</label>
                  <input
                    type="text"
                    required
                    value={suiteForm.name}
                    onChange={(e) => setSuiteForm({ ...suiteForm, name: e.target.value })}
                    className="w-full px-3 py-2 bg-background border border-input rounded-md focus:ring-2 focus:ring-ring focus:border-ring"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-foreground mb-1">Description</label>
                  <textarea
                    value={suiteForm.description}
                    onChange={(e) => setSuiteForm({ ...suiteForm, description: e.target.value })}
                    className="w-full px-3 py-2 bg-background border border-input rounded-md focus:ring-2 focus:ring-ring focus:border-ring"
                    rows={2}
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-foreground mb-1">
                    Select Test Cases ({selectedTcIds.length} selected)
                  </label>
                  <div className="border border-input rounded-md max-h-48 overflow-y-auto">
                    {testCases && testCases.length > 0 ? (
                      testCases.map((tc) => (
                        <label key={tc.id} className="flex items-center px-3 py-2 hover:bg-accent/30 cursor-pointer border-b border-border last:border-b-0">
                          <input type="checkbox" checked={selectedTcIds.includes(tc.id)} onChange={() => toggleTc(tc.id)} className="mr-3 accent-primary" />
                          <span className="font-mono text-xs text-primary mr-2">{tc.tc_id}</span>
                          <span className="text-sm text-foreground truncate">{tc.title}</span>
                        </label>
                      ))
                    ) : (
                      <div className="p-4 text-center text-sm text-muted-foreground">No test cases available.</div>
                    )}
                  </div>
                </div>
              </div>
              <div className="px-6 py-4 border-t border-border flex justify-end space-x-3">
                <button type="button" onClick={() => { setShowCreateSuite(false); setSelectedTcIds([]) }} className="px-4 py-2 border border-input rounded-md text-foreground hover:bg-accent/50">Cancel</button>
                <button type="submit" disabled={createSuiteMutation.isPending} className="px-4 py-2 bg-primary text-white rounded-md hover:bg-primary/90 disabled:opacity-50">
                  {createSuiteMutation.isPending ? 'Creating...' : 'Create Suite'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  )
}

function CampaignCard({ campaign, prefix }: { campaign: import('../api/client').TestCampaign; prefix: string }) {
  const total = campaign.total_items
  const progress = 0

  return (
    <Link
      to={`/projects/${prefix}/campaigns/${campaign.id}`}
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

      {campaign.suites && campaign.suites.length > 0 && (
        <div className="mb-3 text-xs text-muted-foreground">
          Suite{campaign.suites.length > 1 ? 's' : ''}:{' '}
          {campaign.suites.map((s, i) => (
            <span key={s.id}>
              {i > 0 && ', '}
              <span className="text-foreground font-medium">{s.suite_id}</span>
              <span className="ml-1">{s.name}</span>
            </span>
          ))}
        </div>
      )}

      {total > 0 && (
        <div>
          <div className="flex items-center justify-between mb-1.5">
            <div className="flex items-center space-x-3 text-xs">
              <span className="text-muted-foreground">Scope items: {campaign.total_items}</span>
              {campaign.bud_run_id && <span className="text-foreground">Bud run #{campaign.bud_run_id}</span>}
            </div>
            <span className="text-xs text-muted-foreground">{campaign.bud_run_status || 'Not linked'}</span>
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
    Scope: { colors: 'bg-blue-500/10 text-blue-700 dark:text-blue-400', icon: FlaskConical },
    'In Progress': { colors: 'bg-blue-500/10 text-blue-700 dark:text-blue-400', icon: FlaskConical },
    Completed: { colors: 'bg-emerald-500/10 text-emerald-700 dark:text-emerald-400', icon: FlaskConical },
    Aborted: { colors: 'bg-red-500/10 text-red-700 dark:text-red-400', icon: FlaskConical },
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
