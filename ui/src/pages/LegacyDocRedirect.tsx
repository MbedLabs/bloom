import { Navigate, useLocation, useParams } from 'react-router'

/** An older defect, suite or campaign address, by database id or document ID, sent to its document address, which replaces a database id by the document ID. */
export default function LegacyDocRedirect({ slug, param }: Readonly<{ slug: string; param: string }>) {
  const params = useParams()
  const location = useLocation()
  return <Navigate to={`/projects/${params.prefix}/docs/${slug}/${params[param]}`} state={location.state} replace />
}
