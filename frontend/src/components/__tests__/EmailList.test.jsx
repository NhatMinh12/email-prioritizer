import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import { EmailList } from '../EmailList'

const mockEmails = [
  {
    id: 'e1',
    sender: 'alice@co.com',
    subject: 'Hello',
    body_preview: null,
    received_at: '2026-03-01T10:00:00Z',
    has_attachments: false,
    thread_length: 1,
    classification: null,
  },
  {
    id: 'e2',
    sender: 'bob@co.com',
    subject: 'Meeting',
    body_preview: null,
    received_at: '2026-03-01T11:00:00Z',
    has_attachments: false,
    thread_length: 1,
    classification: null,
  },
]

describe('EmailList', () => {
  it('renders loading skeleton', () => {
    const { container } = render(
      <EmailList emails={[]} loading={true} error={null} />
    )
    const skeletons = container.querySelectorAll('.animate-pulse')
    expect(skeletons.length).toBe(3)
  })

  it('renders error message', () => {
    render(
      <EmailList emails={[]} loading={false} error="Something went wrong" />
    )
    expect(screen.getByText('Something went wrong')).toBeInTheDocument()
  })

  it('renders empty state', () => {
    render(<EmailList emails={[]} loading={false} error={null} />)
    expect(
      screen.getByText('No emails found. Try syncing your inbox.')
    ).toBeInTheDocument()
  })

  it('renders email cards', () => {
    render(
      <EmailList
        emails={mockEmails}
        loading={false}
        error={null}
        onFeedback={vi.fn()}
      />
    )
    expect(screen.getByText('alice@co.com')).toBeInTheDocument()
    expect(screen.getByText('bob@co.com')).toBeInTheDocument()
  })

  it('passes onFeedback to cards', () => {
    const onFeedback = vi.fn()
    render(
      <EmailList
        emails={mockEmails}
        loading={false}
        error={null}
        onFeedback={onFeedback}
      />
    )
    // Just verify it renders without error — callback tested in EmailCard tests
    expect(screen.getByText('Hello')).toBeInTheDocument()
  })
})
