import type { ProfilePerson } from '../api/client'
import ProfilePicture from './ProfilePicture'

export default function UserIdentity({ user, prefix = '', className = '', pictureClassName = 'w-6 h-6' }: {
  user: ProfilePerson
  prefix?: string
  className?: string
  pictureClassName?: string
}) {
  return <span className={`inline-flex min-w-0 items-center gap-2 align-middle ${className}`}>
    <span aria-hidden="true" className="inline-flex"><ProfilePicture user={user} className={pictureClassName} /></span>
    <span className="truncate">{prefix}{user.full_name}</span>
  </span>
}
