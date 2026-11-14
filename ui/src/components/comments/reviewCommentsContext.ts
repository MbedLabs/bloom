import { createContext, useContext } from 'react'

import type { CommentAnchor } from '../../api/client'

export type Pending = { anchor: CommentAnchor; rect: DOMRect; pageTop: number }

export interface ReviewCommentsState {
  artefactType: string
  artefactId: number
  projectPrefix?: string
  projectId?: number
  selectedId: number | null
  select: (id: number | null) => void
  pending: Pending | null
  setPending: (pending: Pending | null) => void
  composing: Pending | null
  setComposing: (pending: Pending | null) => void
  showResolved: boolean
  setShowResolved: (show: boolean) => void
  commentsShown: boolean
  setCommentsShown: (shown: boolean) => void
}

export const ReviewCommentsContext = createContext<ReviewCommentsState | null>(null)

/** Whether the comments of the surrounding document are shown; undefined outside a ReviewCommentsProvider. */
export function useCommentsShown(): boolean | undefined {
  return useContext(ReviewCommentsContext)?.commentsShown
}
