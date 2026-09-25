import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Edit2, Plus, Trash2, Users, X } from 'lucide-react'
import {
  BaseRole,
  Group,
  GroupInput,
  groupsApi,
  Policy,
  PolicyInput,
  policiesApi,
  projectsApi,
  usersApi,
} from '../api/client'
import { useToast } from '../components/useToast'
import { DOC_TYPE_LABELS, type DocType } from '../types/doc'

const EXTERNAL_DOC_TYPES = Object.keys(DOC_TYPE_LABELS) as DocType[]

const BASE_ROLES: BaseRole[] = ['external', 'maintainer', 'admin']

export default function GroupsPage() {
  const queryClient = useQueryClient()
  const toast = useToast()

  const { data: policies } = useQuery({ queryKey: ['policies'], queryFn: policiesApi.list })
  const { data: groups } = useQuery({ queryKey: ['groups'], queryFn: groupsApi.list })

  const [editingPolicy, setEditingPolicy] = useState<Policy | 'new' | null>(null)
  const [editingGroup, setEditingGroup] = useState<Group | 'new' | null>(null)
  const [managingGroupId, setManagingGroupId] = useState<number | null>(null)

  const invalidatePolicies = () => queryClient.invalidateQueries({ queryKey: ['policies'] })
  const invalidateGroups = () => queryClient.invalidateQueries({ queryKey: ['groups'] })

  const deletePolicy = useMutation({
    mutationFn: (id: number) => policiesApi.delete(id),
    onSuccess: () => {
      invalidatePolicies()
      toast.deleted('Policy')
    },
    onError: (error) => toast.failed('Deleting the policy', error),
  })

  const deleteGroup = useMutation({
    mutationFn: (id: number) => groupsApi.delete(id),
    onSuccess: () => {
      invalidateGroups()
      toast.deleted('Group')
    },
    onError: (error) => toast.failed('Deleting the group', error),
  })

  const policyName = (id: number | null) =>
    (id != null && policies?.find((p) => p.id === id)?.name) || 'None'

  const managingGroup = groups?.find((g) => g.id === managingGroupId) ?? null

  return (
    <div className="p-6 space-y-10">
      <section>
        <div className="flex items-center justify-between mb-4">
          <div>
            <h1 className="text-xl font-semibold text-foreground">Groups</h1>
            <p className="text-sm text-muted-foreground mt-1">
              A group carries a policy and is granted projects. Its members gain that access.
            </p>
          </div>
          <button
            onClick={() => setEditingGroup('new')}
            className="inline-flex items-center gap-1.5 px-3 py-2 bg-primary text-white text-sm font-medium rounded-lg hover:bg-primary/90"
          >
            <Plus className="h-4 w-4" /> New group
          </button>
        </div>
        <div className="border border-border rounded-xl overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-muted/50 text-muted-foreground">
              <tr>
                <th className="text-left font-medium px-4 py-2">Name</th>
                <th className="text-left font-medium px-4 py-2">Policy</th>
                <th className="text-left font-medium px-4 py-2">Members</th>
                <th className="text-left font-medium px-4 py-2">Projects</th>
                <th className="px-4 py-2" />
              </tr>
            </thead>
            <tbody>
              {(groups ?? []).map((group) => (
                <tr key={group.id} className="border-t border-border">
                  <td className="px-4 py-2 text-foreground font-medium">{group.name}</td>
                  <td className="px-4 py-2 text-muted-foreground">{policyName(group.policy_id)}</td>
                  <td className="px-4 py-2 text-muted-foreground">{group.members.length}</td>
                  <td className="px-4 py-2 text-muted-foreground">
                    {group.grants.some((g) => g.project_id === null)
                      ? 'All projects'
                      : group.grants.length}
                  </td>
                  <td className="px-4 py-2">
                    <div className="flex items-center justify-end gap-1">
                      <button
                        onClick={() => setManagingGroupId(group.id)}
                        title="Manage members and projects"
                        className="inline-flex items-center gap-1 px-2 py-1 rounded text-xs text-foreground hover:bg-muted"
                      >
                        <Users className="h-3.5 w-3.5" /> Manage
                      </button>
                      <button
                        onClick={() => setEditingGroup(group)}
                        title="Edit group"
                        className="p-1 rounded text-muted-foreground hover:text-foreground"
                      >
                        <Edit2 className="h-3.5 w-3.5" />
                      </button>
                      <button
                        onClick={() => deleteGroup.mutate(group.id)}
                        title="Delete group"
                        className="p-1 rounded text-muted-foreground hover:text-destructive"
                      >
                        <Trash2 className="h-3.5 w-3.5" />
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
              {groups?.length === 0 && (
                <tr>
                  <td colSpan={5} className="px-4 py-6 text-center text-muted-foreground">
                    No groups yet.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </section>

      <section>
        <div className="flex items-center justify-between mb-4">
          <div>
            <h1 className="text-xl font-semibold text-foreground">Policies</h1>
            <p className="text-sm text-muted-foreground mt-1">
              Named permission sets. The shipped defaults are protected.
            </p>
          </div>
          <button
            onClick={() => setEditingPolicy('new')}
            className="inline-flex items-center gap-1.5 px-3 py-2 bg-primary text-white text-sm font-medium rounded-lg hover:bg-primary/90"
          >
            <Plus className="h-4 w-4" /> New policy
          </button>
        </div>
        <div className="border border-border rounded-xl overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-muted/50 text-muted-foreground">
              <tr>
                <th className="text-left font-medium px-4 py-2">Name</th>
                <th className="text-left font-medium px-4 py-2">Base role</th>
                <th className="text-left font-medium px-4 py-2">Document types</th>
                <th className="px-4 py-2" />
              </tr>
            </thead>
            <tbody>
              {(policies ?? []).map((policy) => (
                <tr key={policy.id} className="border-t border-border">
                  <td className="px-4 py-2 text-foreground font-medium">
                    {policy.name}
                    {policy.is_default && (
                      <span className="ml-2 px-1.5 py-0.5 rounded text-[10px] font-semibold uppercase bg-muted text-muted-foreground">
                        Default
                      </span>
                    )}
                  </td>
                  <td className="px-4 py-2 text-muted-foreground">{policy.base_role}</td>
                  <td className="px-4 py-2 text-muted-foreground">
                    {policy.base_role !== 'external'
                      ? 'All'
                      : policy.doc_tag_scope === null
                        ? 'All'
                        : policy.doc_tag_scope.join(', ') || 'None'}
                  </td>
                  <td className="px-4 py-2">
                    <div className="flex items-center justify-end gap-1">
                      <button
                        onClick={() => setEditingPolicy(policy)}
                        title={`Edit ${policy.name}`}
                        className="p-1 rounded text-muted-foreground hover:text-foreground"
                      >
                        <Edit2 className="h-3.5 w-3.5" />
                      </button>
                      <button
                        onClick={() => deletePolicy.mutate(policy.id)}
                        disabled={policy.is_default}
                        title={policy.is_default ? 'Default policies cannot be deleted' : `Delete ${policy.name}`}
                        className="p-1 rounded text-muted-foreground hover:text-destructive disabled:opacity-30 disabled:hover:text-muted-foreground"
                      >
                        <Trash2 className="h-3.5 w-3.5" />
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      {editingPolicy && (
        <PolicyModal
          policy={editingPolicy === 'new' ? null : editingPolicy}
          onClose={() => setEditingPolicy(null)}
          onSaved={() => {
            invalidatePolicies()
            setEditingPolicy(null)
          }}
        />
      )}
      {editingGroup && (
        <GroupModal
          group={editingGroup === 'new' ? null : editingGroup}
          policies={policies ?? []}
          onClose={() => setEditingGroup(null)}
          onSaved={() => {
            invalidateGroups()
            setEditingGroup(null)
          }}
        />
      )}
      {managingGroup && (
        <ManageGroupModal
          group={managingGroup}
          onClose={() => setManagingGroupId(null)}
          onChanged={invalidateGroups}
        />
      )}
    </div>
  )
}

function ModalShell({ title, onClose, children }: {
  title: string
  onClose: () => void
  children: React.ReactNode
}) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50" onClick={onClose}>
      <div
        className="bg-card border border-border rounded-xl shadow-elegant p-6 w-full max-w-md"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold text-foreground">{title}</h2>
          <button onClick={onClose} title="Close" className="p-1 rounded text-muted-foreground hover:text-foreground">
            <X className="h-4 w-4" />
          </button>
        </div>
        {children}
      </div>
    </div>
  )
}

const inputClass =
  'w-full px-3 py-2 bg-background border border-input rounded-lg text-sm text-foreground'
const submitClass =
  'w-full py-2 bg-gradient-to-r from-primary to-[#6b7280] text-white text-sm font-medium rounded-lg hover:opacity-90 disabled:opacity-50'

function PolicyModal({ policy, onClose, onSaved }: {
  policy: Policy | null
  onClose: () => void
  onSaved: () => void
}) {
  const toast = useToast()
  const [name, setName] = useState(policy?.name ?? '')
  const [description, setDescription] = useState(policy?.description ?? '')
  const [baseRole, setBaseRole] = useState<BaseRole>(policy?.base_role ?? 'external')
  const [docTypes, setDocTypes] = useState<string[]>(policy?.doc_tag_scope ?? [])
  const isDefault = policy?.is_default ?? false

  const save = useMutation({
    mutationFn: () => {
      const payload: PolicyInput = { description, doc_tag_scope: baseRole === 'external' ? docTypes : null }
      if (!isDefault) {
        payload.name = name
        payload.base_role = baseRole
      }
      return policy ? policiesApi.update(policy.id, payload) : policiesApi.create({ ...payload, name, base_role: baseRole })
    },
    onSuccess: () => {
      toast.saved('Policy')
      onSaved()
    },
    onError: (error) => toast.failed('Saving the policy', error),
  })

  const toggleDocType = (dt: string) =>
    setDocTypes((prev) => (prev.includes(dt) ? prev.filter((x) => x !== dt) : [...prev, dt]))

  return (
    <ModalShell title={policy ? 'Edit policy' : 'New policy'} onClose={onClose}>
      <form
        onSubmit={(e) => {
          e.preventDefault()
          save.mutate()
        }}
        className="space-y-3"
      >
        <div>
          <label className="block text-sm font-medium text-foreground mb-1">Name</label>
          <input
            value={name}
            onChange={(e) => setName(e.target.value)}
            required
            disabled={isDefault}
            title="Policy name"
            className={inputClass + (isDefault ? ' opacity-60' : '')}
          />
        </div>
        <div>
          <label className="block text-sm font-medium text-foreground mb-1">Description</label>
          <input
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            title="Description"
            className={inputClass}
          />
        </div>
        <div>
          <label className="block text-sm font-medium text-foreground mb-1">Base role</label>
          <select
            value={baseRole}
            onChange={(e) => setBaseRole(e.target.value as BaseRole)}
            disabled={isDefault}
            title="Base role"
            className={inputClass + (isDefault ? ' opacity-60' : '')}
          >
            {BASE_ROLES.map((r) => (
              <option key={r} value={r}>{r}</option>
            ))}
          </select>
          {isDefault && (
            <p className="text-xs text-muted-foreground mt-1">A default policy's name and base role are fixed.</p>
          )}
        </div>
        {baseRole === 'external' && (
          <div>
            <label className="block text-sm font-medium text-foreground mb-1">
              Document types (empty means every type)
            </label>
            <div className="flex flex-wrap gap-1.5">
              {EXTERNAL_DOC_TYPES.map((dt) => (
                <button
                  type="button"
                  key={dt}
                  onClick={() => toggleDocType(dt)}
                  className={
                    'px-2 py-0.5 rounded text-xs border ' +
                    (docTypes.includes(dt)
                      ? 'bg-primary text-white border-primary'
                      : 'bg-background text-muted-foreground border-input')
                  }
                >
                  {dt}
                </button>
              ))}
            </div>
          </div>
        )}
        <button type="submit" disabled={save.isPending} className={submitClass}>
          {save.isPending ? 'Saving…' : 'Save policy'}
        </button>
      </form>
    </ModalShell>
  )
}

function GroupModal({ group, policies, onClose, onSaved }: {
  group: Group | null
  policies: Policy[]
  onClose: () => void
  onSaved: () => void
}) {
  const toast = useToast()
  const [name, setName] = useState(group?.name ?? '')
  const [description, setDescription] = useState(group?.description ?? '')
  const [policyId, setPolicyId] = useState<number | null>(group?.policy_id ?? null)

  const save = useMutation({
    mutationFn: () => {
      const payload: GroupInput = { name, description, policy_id: policyId }
      return group ? groupsApi.update(group.id, payload) : groupsApi.create(payload)
    },
    onSuccess: () => {
      toast.saved('Group')
      onSaved()
    },
    onError: (error) => toast.failed('Saving the group', error),
  })

  return (
    <ModalShell title={group ? 'Edit group' : 'New group'} onClose={onClose}>
      <form
        onSubmit={(e) => {
          e.preventDefault()
          save.mutate()
        }}
        className="space-y-3"
      >
        <div>
          <label className="block text-sm font-medium text-foreground mb-1">Name</label>
          <input value={name} onChange={(e) => setName(e.target.value)} required title="Group name" className={inputClass} />
        </div>
        <div>
          <label className="block text-sm font-medium text-foreground mb-1">Description</label>
          <input value={description} onChange={(e) => setDescription(e.target.value)} title="Description" className={inputClass} />
        </div>
        <div>
          <label className="block text-sm font-medium text-foreground mb-1">Policy</label>
          <select
            value={policyId ?? ''}
            onChange={(e) => setPolicyId(e.target.value ? Number(e.target.value) : null)}
            title="Policy"
            className={inputClass}
          >
            <option value="">None</option>
            {policies.map((p) => (
              <option key={p.id} value={p.id}>{p.name}</option>
            ))}
          </select>
        </div>
        <button type="submit" disabled={save.isPending} className={submitClass}>
          {save.isPending ? 'Saving…' : 'Save group'}
        </button>
      </form>
    </ModalShell>
  )
}

function ManageGroupModal({ group, onClose, onChanged }: {
  group: Group
  onClose: () => void
  onChanged: () => void
}) {
  const toast = useToast()
  const { data: users } = useQuery({ queryKey: ['users'], queryFn: usersApi.list })
  const { data: projects } = useQuery({ queryKey: ['projects'], queryFn: projectsApi.list })
  const [userId, setUserId] = useState('')
  const [projectId, setProjectId] = useState('')

  const run = (fn: () => Promise<unknown>, doing: string) =>
    fn()
      .then(() => onChanged())
      .catch((error) => toast.failed(doing, error))

  const memberIds = new Set(group.members.map((m) => m.user_id))
  const grantedProjectIds = new Set(group.grants.map((g) => g.project_id))

  return (
    <ModalShell title={`Manage ${group.name}`} onClose={onClose}>
      <div className="space-y-5">
        <div>
          <h3 className="text-sm font-medium text-foreground mb-2">Members</h3>
          <ul className="space-y-1 mb-2">
            {group.members.map((m) => (
              <li key={m.user_id} className="flex items-center justify-between text-sm">
                <span className="text-foreground">{m.full_name} <span className="text-muted-foreground">({m.email})</span></span>
                <button
                  onClick={() => run(() => groupsApi.removeMember(group.id, m.user_id), 'Removing the member')}
                  title="Remove member"
                  className="p-1 rounded text-muted-foreground hover:text-destructive"
                >
                  <X className="h-3.5 w-3.5" />
                </button>
              </li>
            ))}
            {group.members.length === 0 && <li className="text-sm text-muted-foreground">No members yet.</li>}
          </ul>
          <div className="flex gap-2">
            <select value={userId} onChange={(e) => setUserId(e.target.value)} title="Add member" className={inputClass}>
              <option value="">Add a user…</option>
              {(users ?? [])
                .filter((u) => !memberIds.has(u.id))
                .map((u) => (
                  <option key={u.id} value={u.id}>{u.full_name} ({u.email})</option>
                ))}
            </select>
            <button
              disabled={!userId}
              onClick={() =>
                run(() => groupsApi.addMember(group.id, Number(userId)), 'Adding the member').then(() => setUserId(''))
              }
              className="px-3 py-2 bg-primary text-white text-sm rounded-lg hover:bg-primary/90 disabled:opacity-50"
            >
              Add
            </button>
          </div>
        </div>

        <div>
          <h3 className="text-sm font-medium text-foreground mb-2">Project grants</h3>
          <ul className="space-y-1 mb-2">
            {group.grants.map((grant) => (
              <li key={grant.id} className="flex items-center justify-between text-sm">
                <span className="text-foreground">
                  {grant.project_id === null
                    ? 'All projects'
                    : projects?.find((p) => p.id === grant.project_id)?.name ?? `Project ${grant.project_id}`}
                </span>
                <button
                  onClick={() => run(() => groupsApi.removeGrant(group.id, grant.id), 'Removing the grant')}
                  title="Remove grant"
                  className="p-1 rounded text-muted-foreground hover:text-destructive"
                >
                  <X className="h-3.5 w-3.5" />
                </button>
              </li>
            ))}
            {group.grants.length === 0 && <li className="text-sm text-muted-foreground">No projects granted.</li>}
          </ul>
          <div className="flex gap-2">
            <select value={projectId} onChange={(e) => setProjectId(e.target.value)} title="Grant a project" className={inputClass}>
              <option value="">Grant a project…</option>
              {!grantedProjectIds.has(null) && <option value="all">All projects</option>}
              {(projects ?? [])
                .filter((p) => !grantedProjectIds.has(p.id))
                .map((p) => (
                  <option key={p.id} value={p.id}>{p.name}</option>
                ))}
            </select>
            <button
              disabled={!projectId}
              onClick={() =>
                run(
                  () => groupsApi.addGrant(group.id, projectId === 'all' ? null : Number(projectId)),
                  'Granting the project',
                ).then(() => setProjectId(''))
              }
              className="px-3 py-2 bg-primary text-white text-sm rounded-lg hover:bg-primary/90 disabled:opacity-50"
            >
              Grant
            </button>
          </div>
        </div>
      </div>
    </ModalShell>
  )
}
