import { notFound } from 'next/navigation'
import { getServerSession, getSessionUser } from '@/lib/auth/server'
import { AdminShell } from '@/components/admin/admin-shell'

export default async function AdminLayout({ children }: { children: React.ReactNode }) {
  const session = await getServerSession()
  if (!session) notFound()
  const user = await getSessionUser(session)
  if (!user?.is_admin) notFound()
  return <AdminShell user={user}>{children}</AdminShell>
}
