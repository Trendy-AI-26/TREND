import { beforeEach, describe, expect, it, vi } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { NextIntlClientProvider } from 'next-intl'
import messages from '@/messages/en.json'

const { push, refresh, signup } = vi.hoisted(() => ({
    push: vi.fn(),
    refresh: vi.fn(),
    signup: vi.fn(),
}))

vi.mock('next/navigation', () => ({
    useRouter: () => ({ push, refresh }),
}))

vi.mock('@/lib/auth/client', async () => {
    const actual = await vi.importActual<typeof import('@/lib/auth/client')>('@/lib/auth/client')
    return { ...actual, authApi: { ...actual.authApi, signup } }
})

import SignUpPage from '../page'

async function submitForm() {
    const user = userEvent.setup()
    render(
        <NextIntlClientProvider locale="en" messages={messages}>
            <SignUpPage />
        </NextIntlClientProvider>,
    )
    await user.type(document.getElementById('full-name')!, 'Test Person')
    await user.type(document.getElementById('email')!, 'person@example.com')
    await user.type(document.getElementById('password')!, 'correct horse battery')
    await user.click(screen.getByRole('button', { name: new RegExp(messages.auth.createAccount, 'i') }))
}

describe('SignUpPage redirect', () => {
    beforeEach(() => {
        push.mockReset()
        refresh.mockReset()
        signup.mockReset()
    })

    it('goes to the dashboard when the server needs no email verification', async () => {
        signup.mockResolvedValue({
            email: 'person@example.com',
            verification_required: false,
            user: {
                id: 'u1',
                email: 'person@example.com',
                full_name: 'Test Person',
                is_admin: false,
                email_verified: false,
            },
        })

        await submitForm()

        await waitFor(() => expect(push).toHaveBeenCalledWith('/dashboard'))
        expect(refresh).toHaveBeenCalledTimes(1)
        expect(push).toHaveBeenCalledTimes(1)
        expect(signup).toHaveBeenCalledWith({
            email: 'person@example.com',
            password: 'correct horse battery',
            full_name: 'Test Person',
        })
    })

    it('goes to verify-code when the server requires email verification', async () => {
        signup.mockResolvedValue({ email: 'person@example.com', verification_required: true })

        await submitForm()

        await waitFor(() =>
            expect(push).toHaveBeenCalledWith('/verify-code?email=person%40example.com&purpose=verify_email'),
        )
        expect(push).toHaveBeenCalledTimes(1)
        expect(refresh).not.toHaveBeenCalled()
    })
})
