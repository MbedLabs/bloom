import UserIdentity from './UserIdentity'
import { UserCheck, UserCog, type LucideIcon } from 'lucide-react'
import { formatDateTime } from '../lib/dateTime'
import { SectionCard } from './DocDetailShell'
import type { SignOffPerson } from '../hooks/useSignOff'

interface SignOffItem {
  reviewer_id?: number | null
  reviewed_by_id?: number | null
  reviewed_at?: string | null
  approver_id?: number | null
  approved_by_id?: number | null
  approved_at?: string | null
  reviewer_can_sign?: boolean | null
  approver_can_sign?: boolean | null
}

interface Mark {
  isPending: boolean
  mutate: () => void
}

function resolveUserName(users: SignOffPerson[] | undefined, userId: number | null | undefined) {
  if (!userId) return 'Unassigned'
  const person = users?.find((u) => u.id === userId)
  return <UserIdentity user={person ?? { id: userId, full_name: `User #${userId}` }} />
}

interface SignOffCardProps {
  title: string
  assigneeLabel: string
  doneLabel: string
  assigneeId?: number | null
  assigneeCanSign?: boolean | null
  doneById?: number | null
  doneAt?: string | null
  users: SignOffPerson[]
  canSign: boolean
  mark: Mark
  buttonClassName: string
  Icon: LucideIcon
  buttonLabel: string
}

function SignOffCard({
  title,
  assigneeLabel,
  doneLabel,
  assigneeId,
  assigneeCanSign,
  doneById,
  doneAt,
  users,
  canSign,
  mark,
  buttonClassName,
  Icon,
  buttonLabel,
}: Readonly<SignOffCardProps>) {
  return (
    <SectionCard title={title}>
      <div className="space-y-3">
        <div>
          <div className="text-xs uppercase tracking-wide text-muted-foreground mb-1">{assigneeLabel}</div>
          <div className="text-sm text-foreground">{resolveUserName(users, assigneeId)}</div>
          {assigneeCanSign === false && <div className="text-xs text-destructive mt-0.5">cannot sign</div>}
        </div>
        <div>
          <div className="text-xs uppercase tracking-wide text-muted-foreground mb-1">{doneLabel}</div>
          <div className="text-sm text-foreground">{resolveUserName(users, doneById)}</div>
          {doneAt && <div className="text-xs text-muted-foreground mt-0.5">{formatDateTime(doneAt)}</div>}
        </div>
        <button
          disabled={!canSign || !assigneeId || mark.isPending}
          onClick={() => mark.mutate()}
          className={buttonClassName}
        >
          <Icon className="h-3.5 w-3.5 mr-1" />
          {buttonLabel}
        </button>
      </div>
    </SectionCard>
  )
}

interface SignOffCardsProps {
  item: SignOffItem
  users: SignOffPerson[]
  canReview: boolean
  canApprove: boolean
  markReviewed: Mark
  markApproved: Mark
}

/** The Review and Approval cards of an artefact: who is assigned, who signed off and when; a sign-off is recorded as the person who signs. */
export default function SignOffCards({ item, users, canReview, canApprove, markReviewed, markApproved }: Readonly<SignOffCardsProps>) {
  return (
    <>
      <SignOffCard
        title="Review"
        assigneeLabel="Reviewer"
        doneLabel="Reviewed by"
        assigneeId={item.reviewer_id}
        assigneeCanSign={item.reviewer_can_sign}
        doneById={item.reviewed_by_id}
        doneAt={item.reviewed_at}
        users={users}
        canSign={canReview}
        mark={markReviewed}
        buttonClassName="w-full inline-flex items-center justify-center px-3 py-1.5 rounded-md bg-amber-500/90 text-white text-xs font-medium hover:bg-amber-500 disabled:opacity-50"
        Icon={UserCheck}
        buttonLabel="Mark Reviewed"
      />

      <SignOffCard
        title="Approval"
        assigneeLabel="Approver"
        doneLabel="Approved by"
        assigneeId={item.approver_id}
        assigneeCanSign={item.approver_can_sign}
        doneById={item.approved_by_id}
        doneAt={item.approved_at}
        users={users}
        canSign={canApprove}
        mark={markApproved}
        buttonClassName="w-full inline-flex items-center justify-center px-3 py-1.5 rounded-md bg-emerald-600 text-white text-xs font-medium hover:bg-emerald-500 disabled:opacity-50"
        Icon={UserCog}
        buttonLabel="Mark Approved"
      />
    </>
  )
}
