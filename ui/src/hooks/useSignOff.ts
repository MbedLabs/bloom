import { useMemo } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { usersApi, type ProfilePerson } from '../api/client'
import { useToast } from '../components/useToast'

export type SignOffPerson = ProfilePerson & { id: number }

/** The people the sign-off cards can name: the project's people, and for an administrator the whole directory. */
export function useSignOffPeople(projectId: number | undefined, isAdmin: boolean): SignOffPerson[] {
  const { data: projectPeople } = useQuery({
    queryKey: ['mentionableUsers', projectId],
    queryFn: () => usersApi.listMentionable(projectId!),
    enabled: !!projectId,
  })
  const { data: directory } = useQuery({
    queryKey: ['users'],
    queryFn: usersApi.list,
    enabled: isAdmin,
  })
  return useMemo<SignOffPerson[]>(
    () => Array.from(new Map([...(projectPeople ?? []), ...(directory ?? [])].map(person => [person.id, person])).values()),
    [projectPeople, directory],
  )
}

interface SignOffOptions {
  queryKey: readonly unknown[]
  activityKey: readonly unknown[]
  noun: string
  setReviewed: () => Promise<unknown>
  setApproved: () => Promise<unknown>
}

/** The review and approval mutations of an artefact, signed by the signed-in user; each updates the cached artefact and reports the outcome. */
export function useSignOff({ queryKey, activityKey, noun, setReviewed, setApproved }: SignOffOptions) {
  const queryClient = useQueryClient()
  const toast = useToast()
  const capitalised = noun.charAt(0).toUpperCase() + noun.slice(1)
  const signed = (updated: unknown, message: string) => {
    queryClient.setQueryData(queryKey, (old: unknown) => {
      if (old && typeof old === 'object') {
        return { ...(old as object), ...(updated as object) }
      }
      return updated
    })
    void queryClient.invalidateQueries({ queryKey })
    void queryClient.invalidateQueries({ queryKey: activityKey })
    toast.notify(message, 'success')
  }
  const markReviewed = useMutation({
    mutationFn: setReviewed,
    onSuccess: (updated) => signed(updated, `${capitalised} marked as reviewed`),
    onError: (err: unknown) => {
      toast.failed(`Marking the ${noun} reviewed`, err)
    },
  })
  const markApproved = useMutation({
    mutationFn: setApproved,
    onSuccess: (updated) => signed(updated, `${capitalised} approved`),
    onError: (err: unknown) => {
      toast.failed(`Approving the ${noun}`, err)
    },
  })
  return { markReviewed, markApproved }
}
