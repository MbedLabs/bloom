import { useEffect, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import {
  extractApiErrorMessage,
  projectMembersApi,
  projectsApi,
  type ProjectMember,
  type ProjectMemberRole,
  usersApi,
} from '../api/client'
import { useAuth } from '../contexts/AuthContext'
import { useProjectByPrefix } from '../hooks/useProjectByPrefix'
import {
  projectDeleteConfirmationMatches,
  projectDeleteConfirmationPhrase,
} from '../lib/projectDelete'
import IntegrationSettingsPanel from '../components/IntegrationSettingsPanel'

const PROJECT_PREFIX_PATTERN = /^[A-Z]{3}$/
const PROJECT_PREFIX_ERROR = 'Use exactly three uppercase letters, e.g. PRJ.'

const STATUS_OPTIONS = ['Active', 'Archived', 'Draft'] as const
const EXTERNAL_DOC_TYPES = ['REQ', 'SPEC', 'TC', 'DES', 'RSK', 'CHG', 'CPT', 'DEF', 'CMP', 'TS', 'PRT', 'RPT', 'STD'] as const

export default function ProjectEdit() {
  const { prefix } = useParams<{ prefix: string }>()
  const navigate = useNavigate()
  const { user } = useAuth()
  const { data: project, isLoading } = useProjectByPrefix(prefix)
  const queryClient = useQueryClient()

  const [name, setName] = useState('')
  const [projectPrefix, setProjectPrefix] = useState('')
  const [description, setDescription] = useState('')
  const [status, setStatus] = useState('Active')
  const [formError, setFormError] = useState('')
  const [confirmDeleteOpen, setConfirmDeleteOpen] = useState(false)
  const [deleteConfirmationText, setDeleteConfirmationText] = useState('')
  const [deleteExpectedPhrase, setDeleteExpectedPhrase] = useState('')
  const [deleteError, setDeleteError] = useState('')

  useEffect(() => {
    if (!project) return
    setName(project.name)
    setProjectPrefix(project.prefix)
    setDescription(project.description || '')
    setStatus(project.status || 'Active')
  }, [project])

  const normalizedPrefix = projectPrefix.trim().toUpperCase()
  const prefixIsValid = PROJECT_PREFIX_PATTERN.test(normalizedPrefix)
  const showPrefixError = projectPrefix.length > 0 && !prefixIsValid

  const updateMutation = useMutation({
    mutationFn: () =>
      projectsApi.update(project!.id, {
        name,
        prefix: normalizedPrefix,
        description: description || undefined,
        status,
      }),
    onSuccess: (updated) => {
      setFormError('')
      queryClient.setQueryData(['projects'], (old: unknown) => old)
      queryClient.invalidateQueries({ queryKey: ['projects'] })
      queryClient.setQueryData(['project-by-prefix', updated.prefix], updated)
      queryClient.invalidateQueries({ queryKey: ['project-by-prefix', updated.prefix] })
      if (updated.prefix !== prefix) {
        navigate(`/projects/${updated.prefix}/edit`, { replace: true })
      }
    },
    onError: (error) => {
      setFormError(extractApiErrorMessage(error, 'Could not update project'))
    },
  })

  const deleteMutation = useMutation({
    mutationFn: () => projectsApi.delete(project!.id),
    onSuccess: () => {
      setDeleteError('')
      queryClient.invalidateQueries({ queryKey: ['projects'] })
      navigate('/projects', { replace: true })
    },
    onError: (error) => {
      setDeleteError(extractApiErrorMessage(error, 'Could not delete project'))
    },
  })

  const isAdmin = user?.role === 'admin'

  const { data: projectList } = useQuery({
    queryKey: ['projects'],
    queryFn: projectsApi.list,
    enabled: isAdmin,
  })

  const { data: projectMembers } = useQuery({
    queryKey: ['project-members', project?.id],
    queryFn: () => projectMembersApi.list(project!.id),
    enabled: isAdmin && !!project?.id,
  })

  const { data: users } = useQuery({
    queryKey: ['users'],
    queryFn: usersApi.list,
    enabled: isAdmin,
  })

  if (isLoading) {
    return <div className="flex items-center justify-center h-64 text-muted-foreground">Loading...</div>
  }

  if (!project) {
    return (
      <div className="bg-destructive/10 border border-destructive/20 rounded-lg p-6 text-center">
        <h3 className="text-lg font-medium text-destructive">Project Not Found</h3>
        <Link to="/projects" className="mt-4 inline-block text-primary hover:text-primary/80">
          &larr; Back to Projects
        </Link>
      </div>
    )
  }

  if (!isAdmin) {
    return (
      <div className="space-y-4 animate-fade-in">
        <div className="flex items-center gap-2 text-sm text-muted-foreground">
          <Link to={`/projects/${prefix}`} className="hover:text-primary transition-colors">
            {project.name}
          </Link>
          <span>/</span>
          <span className="text-foreground">Edit project</span>
        </div>
        <div className="rounded-lg border border-border bg-card p-6 text-sm text-muted-foreground">
          Only administrators can edit project details. You can still view integration status below if applicable.
        </div>
        <IntegrationSettingsPanel projectId={project.id} />
      </div>
    )
  }

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    setFormError('')
    if (!prefixIsValid) {
      setFormError(PROJECT_PREFIX_ERROR)
      return
    }
    updateMutation.mutate()
  }

  const prefixTaken =
    normalizedPrefix !== project.prefix &&
    projectList?.some((p) => p.prefix === normalizedPrefix && p.id !== project.id)

  const deleteConfirmationMatches = projectDeleteConfirmationMatches(
    deleteConfirmationText,
    deleteExpectedPhrase,
  )

  const openDeleteModal = () => {
    setDeleteError('')
    setDeleteConfirmationText('')
    setDeleteExpectedPhrase(projectDeleteConfirmationPhrase(project.prefix))
    setConfirmDeleteOpen(true)
  }

  const closeDeleteModal = () => {
    setDeleteError('')
    setDeleteConfirmationText('')
    setDeleteExpectedPhrase('')
    setConfirmDeleteOpen(false)
  }

  return (
    <div className="space-y-8 animate-fade-in max-w-3xl">
      <div>
        <div className="flex items-center gap-2 text-sm text-muted-foreground mb-1">
          <Link to={`/projects/${prefix}`} className="hover:text-primary transition-colors">
            {project.name}
          </Link>
          <span>/</span>
          <span className="text-foreground">Edit project</span>
        </div>
        <h2 className="text-xl font-bold text-foreground">Edit project</h2>
        <p className="text-sm text-muted-foreground mt-0.5">Update project metadata and external issue tracker.</p>
      </div>

      <form onSubmit={handleSubmit} className="bg-card rounded-lg border border-border shadow-elegant p-6 space-y-4">
        <h3 className="text-sm font-semibold text-foreground uppercase tracking-wide">Project details</h3>
        {formError && (
          <div className="rounded-md border border-red-500/30 bg-red-500/10 px-3 py-2 text-sm text-red-600">{formError}</div>
        )}
        {prefixTaken && (
          <div className="rounded-md border border-amber-500/30 bg-amber-500/10 px-3 py-2 text-sm text-amber-800 dark:text-amber-200">
            Another project already uses prefix {normalizedPrefix}.
          </div>
        )}
        <div>
          <label className="block text-xs font-medium text-muted-foreground uppercase tracking-wider mb-1.5">Name</label>
          <input
            type="text"
            required
            value={name}
            onChange={(e) => setName(e.target.value)}
            title="Project name"
            placeholder="My Project"
            className="w-full px-3 py-2 bg-background border border-input rounded-md text-sm text-foreground focus:ring-2 focus:ring-ring"
          />
        </div>
        <div>
          <label className="block text-xs font-medium text-muted-foreground uppercase tracking-wider mb-1.5">Prefix</label>
          <input
            type="text"
            required
            value={projectPrefix}
            onChange={(e) => setProjectPrefix(e.target.value.toUpperCase())}
            maxLength={3}
            title="Project prefix"
            placeholder="PRJ"
            className={`w-full px-3 py-2 bg-background border rounded-md text-sm font-mono focus:ring-2 focus:ring-ring ${
              showPrefixError ? 'border-red-500/70' : 'border-input'
            }`}
          />
          <p className={`mt-1 text-xs ${showPrefixError ? 'text-red-600' : 'text-muted-foreground'}`}>
            {showPrefixError ? PROJECT_PREFIX_ERROR : 'Item IDs use PRJ-TYP-001.'}
          </p>
        </div>
        <div>
          <label className="block text-xs font-medium text-muted-foreground uppercase tracking-wider mb-1.5">Status</label>
          <select
            value={status}
            onChange={(e) => setStatus(e.target.value)}
            title="Project status"
            className="w-full px-3 py-2 bg-background border border-input rounded-md text-sm"
          >
            {STATUS_OPTIONS.map((s) => (
              <option key={s} value={s}>
                {s}
              </option>
            ))}
          </select>
        </div>
        <div>
          <label className="block text-xs font-medium text-muted-foreground uppercase tracking-wider mb-1.5">Description</label>
          <textarea
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            rows={3}
            title="Project description"
            placeholder="Project description..."
            className="w-full px-3 py-2 bg-background border border-input rounded-md text-sm"
          />
        </div>
        <div className="flex justify-end gap-3 pt-2">
          <Link
            to={`/projects/${prefix}`}
            className="px-4 py-2 border border-border rounded-md text-sm text-muted-foreground hover:bg-accent transition-colors"
          >
            Cancel
          </Link>
          <button
            type="submit"
            disabled={updateMutation.isPending || !prefixIsValid || !!prefixTaken}
            className="px-4 py-2 bg-primary text-primary-foreground rounded-md text-sm font-medium hover:bg-primary/90 disabled:opacity-50"
          >
            {updateMutation.isPending ? 'Saving...' : 'Save project'}
          </button>
        </div>
      </form>

      <section className="rounded-lg border border-destructive/30 bg-card p-6 shadow-elegant">
        <h3 className="text-sm font-semibold uppercase tracking-wide text-destructive">Danger zone</h3>
        <p className="mt-2 text-sm text-muted-foreground">
          Permanently delete this project and its project-scoped data. This action cannot be undone.
        </p>
        <div className="mt-4 flex justify-end">
          <button
            type="button"
            onClick={openDeleteModal}
            className="rounded-md border border-destructive/30 px-4 py-2 text-sm text-destructive transition-colors hover:bg-destructive/10"
          >
            Delete project
          </button>
        </div>
      </section>

      {confirmDeleteOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm">
          <div className="mx-4 w-full max-w-md rounded-lg bg-card p-6 shadow-elegant">
            <h3 className="text-lg font-semibold text-foreground">Delete project?</h3>
            <p className="mt-2 text-sm text-muted-foreground">
              This permanently removes <span className="font-medium text-foreground">{project.name}</span> ({project.prefix}).
              Type <span className="font-mono text-foreground">{deleteExpectedPhrase}</span> to confirm.
            </p>
            <label className="mt-4 block text-xs font-medium uppercase tracking-wider text-muted-foreground">
              Confirmation
              <input
                type="text"
                value={deleteConfirmationText}
                onChange={(e) => setDeleteConfirmationText(e.target.value)}
                autoComplete="off"
                spellCheck={false}
                placeholder={deleteExpectedPhrase}
                className="mt-1.5 w-full rounded-md border border-input bg-background px-3 py-2 text-sm text-foreground focus:ring-2 focus:ring-ring"
              />
            </label>
            {deleteError && (
              <div className="mt-3 rounded-md border border-red-500/30 bg-red-500/10 px-3 py-2 text-sm text-red-600">
                {deleteError}
              </div>
            )}
            <div className="mt-6 flex justify-end gap-2">
              <button
                type="button"
                onClick={closeDeleteModal}
                className="rounded-md border border-input px-4 py-2 text-sm text-foreground transition-colors hover:bg-accent/50"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={() => deleteMutation.mutate()}
                disabled={!deleteConfirmationMatches || deleteMutation.isPending}
                className="rounded-md bg-destructive px-4 py-2 text-sm text-white transition-colors hover:bg-destructive/90 disabled:opacity-50"
              >
                {deleteMutation.isPending ? 'Deleting...' : 'Delete project'}
              </button>
            </div>
          </div>
        </div>
      )}

      <IntegrationSettingsPanel projectId={project.id} />
      <ProjectMembersPanel
        projectId={project.id}
        members={projectMembers ?? []}
        users={users ?? []}
      />
    </div>
  )
}

function ProjectMembersPanel({
  projectId,
  members,
  users,
}: {
  projectId: number
  members: ProjectMember[]
  users: Array<{ id: number; email: string; full_name: string; role: 'admin' | 'maintainer' | 'external' }>
}) {
  const queryClient = useQueryClient()
  const [selectedUserId, setSelectedUserId] = useState('')
  const [selectedRole, setSelectedRole] = useState<ProjectMemberRole>('external')
  const [selectedDocTypes, setSelectedDocTypes] = useState<string[]>(['REQ', 'TC', 'CPT', 'CMP'])
  const [error, setError] = useState('')

  const availableUsers = users.filter(
    (user) => user.role !== 'admin' && !members.some((member) => member.user_id === user.id)
  )

  const createMutation = useMutation({
    mutationFn: () =>
      projectMembersApi.create(projectId, {
        user_id: Number(selectedUserId),
        role: selectedRole,
        doc_types: selectedRole === 'external' ? selectedDocTypes : undefined,
      }),
    onSuccess: () => {
      setError('')
      setSelectedUserId('')
      setSelectedRole('external')
      setSelectedDocTypes(['REQ', 'TC', 'CPT', 'CMP'])
      queryClient.invalidateQueries({ queryKey: ['project-members', projectId] })
    },
    onError: (mutationError) => {
      setError(extractApiErrorMessage(mutationError, 'Could not add project member'))
    },
  })

  const updateMutation = useMutation({
    mutationFn: ({
      membershipId,
      role,
      docTypes,
    }: {
      membershipId: number
      role: ProjectMemberRole
      docTypes: string[]
    }) =>
      projectMembersApi.update(projectId, membershipId, {
        role,
        doc_types: role === 'external' ? docTypes : [],
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['project-members', projectId] })
    },
  })

  const removeMutation = useMutation({
    mutationFn: (membershipId: number) => projectMembersApi.remove(projectId, membershipId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['project-members', projectId] })
    },
  })

  const handleCreate = (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    if (!selectedUserId) {
      setError('Select a user to add to this project.')
      return
    }
    createMutation.mutate()
  }

  return (
    <section className="rounded-lg border border-border bg-card p-6 shadow-elegant">
      <div className="mb-4">
        <h3 className="text-sm font-semibold uppercase tracking-wide text-foreground">Project members</h3>
        <p className="mt-1 text-sm text-muted-foreground">
          Manage per-project access for maintainers and external users.
        </p>
      </div>

      {error && (
        <div className="mb-4 rounded-md border border-red-500/30 bg-red-500/10 px-3 py-2 text-sm text-red-600">
          {error}
        </div>
      )}

      <form onSubmit={handleCreate} className="mb-6 space-y-4 rounded-lg border border-border bg-background/40 p-4">
        <div className="grid gap-4 md:grid-cols-2">
          <div>
            <label className="mb-1.5 block text-xs font-medium uppercase tracking-wider text-muted-foreground">
              User
            </label>
            <select
              value={selectedUserId}
              onChange={(e) => setSelectedUserId(e.target.value)}
              className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
              title="Select user to add"
            >
              <option value="">Select a user</option>
              {availableUsers.map((user) => (
                <option key={user.id} value={user.id}>
                  {user.full_name} ({user.email})
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="mb-1.5 block text-xs font-medium uppercase tracking-wider text-muted-foreground">
              Role
            </label>
            <select
              value={selectedRole}
              onChange={(e) => setSelectedRole(e.target.value as ProjectMemberRole)}
              className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
              title="Project role"
            >
              <option value="external">External</option>
              <option value="maintainer">Maintainer</option>
            </select>
          </div>
        </div>

        {selectedRole === 'external' && (
          <DocTypePicker
            label="External document visibility"
            selected={selectedDocTypes}
            onToggle={(docType, checked) => {
              setSelectedDocTypes((current) =>
                checked ? [...current, docType] : current.filter((value) => value !== docType)
              )
            }}
          />
        )}

        <div className="flex justify-end">
          <button
            type="submit"
            disabled={createMutation.isPending || !selectedUserId}
            className="rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90 disabled:opacity-50"
          >
            {createMutation.isPending ? 'Adding...' : 'Add member'}
          </button>
        </div>
      </form>

      <div className="space-y-3">
        {members.length === 0 ? (
          <div className="rounded-md border border-border bg-background/40 px-4 py-3 text-sm text-muted-foreground">
            No explicit project members yet.
          </div>
        ) : (
          members.map((member) => (
            <ProjectMemberRow
              key={member.id}
              member={member}
              onSave={(role, docTypes) =>
                updateMutation.mutate({ membershipId: member.id, role, docTypes })
              }
              onRemove={() => removeMutation.mutate(member.id)}
              isSaving={updateMutation.isPending}
              isRemoving={removeMutation.isPending}
            />
          ))
        )}
      </div>
    </section>
  )
}

function ProjectMemberRow({
  member,
  onSave,
  onRemove,
  isSaving,
  isRemoving,
}: {
  member: ProjectMember
  onSave: (role: ProjectMemberRole, docTypes: string[]) => void
  onRemove: () => void
  isSaving: boolean
  isRemoving: boolean
}) {
  const [role, setRole] = useState<ProjectMemberRole>(member.role)
  const [docTypes, setDocTypes] = useState<string[]>(member.doc_types)

  return (
    <div className="rounded-lg border border-border bg-background/40 p-4">
      <div className="mb-3 flex flex-col gap-1 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <p className="text-sm font-medium text-foreground">{member.full_name}</p>
          <p className="text-xs text-muted-foreground">{member.email}</p>
        </div>
        <button
          type="button"
          onClick={onRemove}
          disabled={isRemoving}
          className="rounded-md border border-red-500/30 px-3 py-1.5 text-sm text-red-600 hover:bg-red-500/10 disabled:opacity-50"
        >
          Remove
        </button>
      </div>

      <div className="grid gap-4 md:grid-cols-[180px_1fr]">
        <div>
          <label className="mb-1.5 block text-xs font-medium uppercase tracking-wider text-muted-foreground">
            Role
          </label>
          <select
            value={role}
            onChange={(e) => setRole(e.target.value as ProjectMemberRole)}
            className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
            title={`Project role for ${member.full_name}`}
          >
            <option value="external">External</option>
            <option value="maintainer">Maintainer</option>
          </select>
        </div>

        {role === 'external' ? (
          <DocTypePicker
            label="External document visibility"
            selected={docTypes}
            onToggle={(docType, checked) => {
              setDocTypes((current) =>
                checked ? [...current, docType] : current.filter((value) => value !== docType)
              )
            }}
          />
        ) : (
          <div className="rounded-md border border-border bg-card px-3 py-2 text-sm text-muted-foreground">
            Maintainers can access the full project surface.
          </div>
        )}
      </div>

      <div className="mt-4 flex justify-end">
        <button
          type="button"
          onClick={() => onSave(role, docTypes)}
          disabled={isSaving}
          className="rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90 disabled:opacity-50"
        >
          Save member settings
        </button>
      </div>
    </div>
  )
}

function DocTypePicker({
  label,
  selected,
  onToggle,
}: {
  label: string
  selected: string[]
  onToggle: (docType: string, checked: boolean) => void
}) {
  return (
    <div>
      <p className="mb-1.5 text-xs font-medium uppercase tracking-wider text-muted-foreground">
        {label}
      </p>
      <div className="grid gap-2 sm:grid-cols-3">
        {EXTERNAL_DOC_TYPES.map((docType) => (
          <label key={docType} className="flex items-center gap-2 rounded-md border border-border px-3 py-2 text-sm">
            <input
              type="checkbox"
              checked={selected.includes(docType)}
              onChange={(e) => onToggle(docType, e.target.checked)}
            />
            <span>{docType}</span>
          </label>
        ))}
      </div>
    </div>
  )
}
