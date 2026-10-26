import { cleanup, render, screen, within } from '@testing-library/react'
import { NextIntlClientProvider } from 'next-intl'
import { afterEach, describe, expect, it } from 'vitest'
import messages from '@/messages/en.json'
import { DailyChart } from './daily-chart'

afterEach(cleanup)
function chart(daily: { date: string; succeeded: number; failed: number }[]) {
  return render(<NextIntlClientProvider locale="en" messages={messages}><DailyChart daily={daily} /></NextIntlClientProvider>)
}
describe('DailyChart', () => {
  it('exposes an accessible title, daily bars and exact tabular values', () => {
    const { container } = chart([{ date: '2026-01-01', succeeded: 4, failed: 2 }])
    expect(screen.getByRole('img', { name: /Daily generations/ })).toBeInTheDocument()
    expect(container.querySelectorAll('rect')).toHaveLength(2)
    expect(within(screen.getByRole('table', { hidden: true })).getByText('4')).toBeInTheDocument()
    expect(container.querySelector('g title')).toHaveTextContent('Succeeded 4, Failed 2')
  })
  it('does not divide by zero for an all-zero series', () => {
    const { container } = chart([{ date: '2026-01-01', succeeded: 0, failed: 0 }])
    expect(container.innerHTML).not.toMatch(/NaN|Infinity/)
    expect(container.querySelector('rect')).toHaveAttribute('height', '0')
  })
  it('renders safely with no data', () => {
    const { container } = chart([])
    expect(screen.getByRole('img')).toBeInTheDocument()
    expect(container.querySelectorAll('rect')).toHaveLength(0)
  })
})
