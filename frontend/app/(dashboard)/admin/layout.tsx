import { notFound } from 'next/navigation'
import { getServerSession, getSessionUser } from '@/lib/auth/server'

// Server-side operator gate. The backend `/admin/*` 403 is the real security
// control; this hides the Admin UI from non-operators without leaking the
// allow-list. notFound() is a Server Component API, so this layout is a Server
// Component that resolves is_admin from the backend `GET /auth/session` before
// rendering any admin view.
//
// This runs in Node (not the browser), so the helper calls the backend at the
// absolute, server-reachable NEXT_SERVER_API_URL (the same address the
// next.config rewrite targets), not the browser-relative `/api` path.
export default async function AdminLayout({
  children,
}: {
  children: React.ReactNode
}) {
  const session = await getServerSession()

  if (!session) {
    notFound()
  }

  const user = await getSessionUser(session)

  if (!user?.is_admin) {
    notFound()
  }

  return <>{children}</>
}
