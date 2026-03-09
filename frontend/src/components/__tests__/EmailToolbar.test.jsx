import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { EmailToolbar } from '../EmailToolbar'

const defaultProps = {
  priorityFilter: '',
  onFilterChange: vi.fn(),
  onSync: vi.fn(),
  onClassify: vi.fn(),
  syncing: false,
  classifying: false,
}

describe('EmailToolbar', () => {
  it('renders filter select with all options', () => {
    render(<EmailToolbar {...defaultProps} />)
    expect(screen.getByText('All priorities')).toBeInTheDocument()
    expect(screen.getByText('High')).toBeInTheDocument()
    expect(screen.getByText('Medium')).toBeInTheDocument()
    expect(screen.getByText('Low')).toBeInTheDocument()
  })

  it('calls onFilterChange when filter changes', () => {
    const onFilterChange = vi.fn()
    render(<EmailToolbar {...defaultProps} onFilterChange={onFilterChange} />)

    fireEvent.change(screen.getByRole('combobox'), {
      target: { value: 'high' },
    })
    expect(onFilterChange).toHaveBeenCalledWith('high')
  })

  it('renders Sync Inbox button', () => {
    render(<EmailToolbar {...defaultProps} />)
    expect(screen.getByText('Sync Inbox')).toBeInTheDocument()
  })

  it('shows Syncing... when syncing', () => {
    render(<EmailToolbar {...defaultProps} syncing={true} />)
    expect(screen.getByText('Syncing...')).toBeInTheDocument()
    expect(screen.getByText('Syncing...')).toBeDisabled()
  })

  it('calls onSync when clicked', () => {
    const onSync = vi.fn()
    render(<EmailToolbar {...defaultProps} onSync={onSync} />)
    fireEvent.click(screen.getByText('Sync Inbox'))
    expect(onSync).toHaveBeenCalled()
  })

  it('renders Classify button', () => {
    render(<EmailToolbar {...defaultProps} />)
    expect(screen.getByText('Classify')).toBeInTheDocument()
  })

  it('shows Classifying... when classifying', () => {
    render(<EmailToolbar {...defaultProps} classifying={true} />)
    expect(screen.getByText('Classifying...')).toBeInTheDocument()
    expect(screen.getByText('Classifying...')).toBeDisabled()
  })

  it('calls onClassify when clicked', () => {
    const onClassify = vi.fn()
    render(<EmailToolbar {...defaultProps} onClassify={onClassify} />)
    fireEvent.click(screen.getByText('Classify'))
    expect(onClassify).toHaveBeenCalled()
  })
})
