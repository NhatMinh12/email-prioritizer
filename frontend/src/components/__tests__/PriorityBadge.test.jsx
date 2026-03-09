import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { PriorityBadge } from '../PriorityBadge'

describe('PriorityBadge', () => {
  it('renders priority label', () => {
    render(<PriorityBadge priority="high" />)
    expect(screen.getByText('high')).toBeInTheDocument()
  })

  it('applies high priority style', () => {
    render(<PriorityBadge priority="high" />)
    const badge = screen.getByText('high')
    expect(badge.className).toContain('bg-priority-high')
  })

  it('applies medium priority style', () => {
    render(<PriorityBadge priority="medium" />)
    expect(screen.getByText('medium').className).toContain('bg-priority-medium')
  })

  it('applies low priority style', () => {
    render(<PriorityBadge priority="low" />)
    expect(screen.getByText('low').className).toContain('bg-priority-low')
  })

  it('shows urgency label for non-normal urgency', () => {
    render(<PriorityBadge priority="high" urgency="urgent" />)
    expect(screen.getByText('Urgent')).toBeInTheDocument()
  })

  it('shows time-sensitive urgency label', () => {
    render(<PriorityBadge priority="medium" urgency="time_sensitive" />)
    expect(screen.getByText('Time-sensitive')).toBeInTheDocument()
  })

  it('does not show urgency for normal', () => {
    render(<PriorityBadge priority="low" urgency="normal" />)
    expect(screen.queryByText('Normal')).not.toBeInTheDocument()
  })

  it('does not show urgency when not provided', () => {
    render(<PriorityBadge priority="low" />)
    const container = screen.getByText('low').parentElement
    expect(container.children).toHaveLength(1)
  })

  it('handles unknown priority gracefully', () => {
    render(<PriorityBadge priority="unknown" />)
    const badge = screen.getByText('unknown')
    expect(badge.className).toContain('bg-gray-200')
  })
})
