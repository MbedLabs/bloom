import { Navigate, useLocation, useParams } from 'react-router'

/** An older defect, suite or campaign address sent to its document address; a defect may be named by database id or document ID, a suite or campaign by document ID only. */
export default function LegacyDocRedirect({ slug, param }: Readonly<{ slug: string; param: string }>) {
  const params = useParams()
  const location = useLocation()
  return <Navigate to={`/projects/${params.prefix}/docs/${slug}/${params[param]}`} state={location.state} replace />
}
