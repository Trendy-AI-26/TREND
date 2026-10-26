import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { NextIntlClientProvider } from 'next-intl'
import { afterEach, describe, expect, it, vi } from 'vitest'
import messages from '@/messages/en.json'
import { AdminSidebar } from './admin-shell'

const mocks = vi.hoisted(() => ({ push: vi.fn(), refresh: vi.fn(), logout: vi.fn().mockResolvedValue(undefined) }))
vi.mock('next/navigation', () => ({ usePathname: () => '/admin/users', useRouter: () => ({ push: mocks.push, refresh: mocks.refresh }) }))
vi.mock('@/lib/api', () => ({ logout: mocks.logout }))
afterEach(() => { cleanup(); vi.clearAllMocks() })
describe('AdminSidebar', () => {
  it('links all six admin routes and the app without a brand switcher', () => {
    render(<NextIntlClientProvider locale="en" messages={messages}><AdminSidebar user={{ id: 'admin', email: 'admin@example.com', full_name: 'Admin Name', is_admin: true, email_verified: true }} /></NextIntlClientProvider>)
    for (const [name, href] of [['Overview', '/admin'], ['Users', '/admin/users'], ['Brands', '/admin/brands'], ['Generations', '/admin/generations'], ['Trends', '/admin/trends'], ['Audit log', '/admin/audit-log'], ['Back to app', '/dashboard']]) {
      expect(screen.getByRole('link', { name })).toHaveAttribute('href', href)
    }
    expect(screen.getByRole('link', { name: 'Users' })).toHaveAttribute('aria-current', 'page')
    expect(screen.getByText('Admin Name')).toBeInTheDocument()
    expect(screen.queryByText('Current brand')).not.toBeInTheDocument()
  })
  it('reuses logout and returns to login', async () => {
    render(<NextIntlClientProvider locale="en" messages={messages}><AdminSidebar user={{ id: 'admin', email: 'admin@example.com', full_name: null, is_admin: true, email_verified: true }} /></NextIntlClientProvider>)
    fireEvent.click(screen.getByRole('button', { name: 'Log out' }))
    await waitFor(() => expect(mocks.push).toHaveBeenCalledWith('/login'))
    expect(mocks.logout).toHaveBeenCalledOnce()
    expect(mocks.refresh).toHaveBeenCalledOnce()
  })
})
