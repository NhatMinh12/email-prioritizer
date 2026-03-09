import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { EmailCard } from '../EmailCard'

const baseEmail = {
  id: 'e1',
  sender: 'alice@example.com',
  subject: 'Project update',
  body_preview: 'Here is the latest status...',
  received_at: '2026-03-01T14:30:00Z',
  has_attachments: false,
  thread_length: 1,
  classification: null,
}

const classifiedEmail = {
  ...baseEmail,
  classification: {
    priority: 'high',
    urgency: 'urgent',
    needs_response: true,
    reason: 'Manager requesting update',
    action_items: ['Send report', 'Schedule meeting'],
    feedback: null,
  },
}

describe('EmailCard', () => {
  it('renders sender and subject', () => {
    render(<EmailCard email={baseEmail} />)
    expect(screen.getByText('alice@example.com')).toBeInTheDocument()
    expect(screen.getByText('Project update')).toBeInTheDocument()
  })

  it('renders body preview', () => {
    render(<EmailCard email={baseEmail} />)
    expect(
      screen.getByText('Here is the latest status...')
    ).toBeInTheDocument()
  })

  it('renders formatted date', () => {
    render(<EmailCard email={baseEmail} />)
    // Date format varies by locale, just check something renders
    const dateEl = screen.getByText(/Mar/i)
    expect(dateEl).toBeInTheDocument()
  })

  it('shows attachment icon when has_attachments is true', () => {
    render(<EmailCard email={{ ...baseEmail, has_attachments: true }} />)
    // SVG paperclip icon should be present
    const svgs = document.querySelectorAll('svg')
    expect(svgs.length).toBeGreaterThan(0)
  })

  it('shows thread count when > 1', () => {
    render(<EmailCard email={{ ...baseEmail, thread_length: 5 }} />)
    expect(screen.getByText('(5)')).toBeInTheDocument()
  })

  it('does not show thread count for single messages', () => {
    render(<EmailCard email={baseEmail} />)
    expect(screen.queryByText('(1)')).not.toBeInTheDocument()
  })

  it('shows priority badge when classified', () => {
    render(<EmailCard email={classifiedEmail} />)
    expect(screen.getByText('high')).toBeInTheDocument()
  })

  it('expands on click to show classification details', () => {
    render(<EmailCard email={classifiedEmail} />)

    expect(
      screen.queryByText('Manager requesting update')
    ).not.toBeInTheDocument()

    fireEvent.click(screen.getByText('Project update'))

    expect(screen.getByText('Manager requesting update')).toBeInTheDocument()
    expect(screen.getByText('Needs response')).toBeInTheDocument()
    expect(screen.getByText('Send report')).toBeInTheDocument()
    expect(screen.getByText('Schedule meeting')).toBeInTheDocument()
  })

  it('shows "Not yet classified" when expanded without classification', () => {
    render(<EmailCard email={baseEmail} />)
    fireEvent.click(screen.getByText('Project update'))
    expect(screen.getByText('Not yet classified')).toBeInTheDocument()
  })

  it('collapses on second click', () => {
    render(<EmailCard email={classifiedEmail} />)

    fireEvent.click(screen.getByText('Project update'))
    expect(screen.getByText('Manager requesting update')).toBeInTheDocument()

    fireEvent.click(screen.getByText('Project update'))
    expect(
      screen.queryByText('Manager requesting update')
    ).not.toBeInTheDocument()
  })

  it('renders feedback buttons when expanded and onFeedback provided', () => {
    render(<EmailCard email={classifiedEmail} onFeedback={vi.fn()} />)
    fireEvent.click(screen.getByText('Project update'))

    expect(screen.getByText('Was this accurate?')).toBeInTheDocument()
    expect(screen.getByText('Yes')).toBeInTheDocument()
    expect(screen.getByText('No')).toBeInTheDocument()
  })

  it('calls onFeedback with correct arguments', () => {
    const onFeedback = vi.fn()
    render(<EmailCard email={classifiedEmail} onFeedback={onFeedback} />)
    fireEvent.click(screen.getByText('Project update'))

    fireEvent.click(screen.getByText('Yes'))
    expect(onFeedback).toHaveBeenCalledWith('e1', 'correct')
  })

  it('calls onFeedback with incorrect', () => {
    const onFeedback = vi.fn()
    render(<EmailCard email={classifiedEmail} onFeedback={onFeedback} />)
    fireEvent.click(screen.getByText('Project update'))

    fireEvent.click(screen.getByText('No'))
    expect(onFeedback).toHaveBeenCalledWith('e1', 'incorrect')
  })

  it('disables feedback button when feedback already given', () => {
    const emailWithFeedback = {
      ...classifiedEmail,
      classification: { ...classifiedEmail.classification, feedback: 'correct' },
    }
    render(<EmailCard email={emailWithFeedback} onFeedback={vi.fn()} />)
    fireEvent.click(screen.getByText('Project update'))

    const yesBtn = screen.getByText('Yes')
    expect(yesBtn).toBeDisabled()
  })
})
