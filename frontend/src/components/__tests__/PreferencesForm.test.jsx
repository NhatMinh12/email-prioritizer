import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { PreferencesForm } from '../PreferencesForm'

const mockPrefs = {
  important_senders: ['boss@co.com', 'cto@co.com'],
  important_keywords: ['urgent', 'deadline'],
  response_rate: 0.75,
}

describe('PreferencesForm', () => {
  it('renders with existing preferences', () => {
    render(
      <PreferencesForm preferences={mockPrefs} saving={false} onSave={vi.fn()} />
    )
    const sendersInput = screen.getByLabelText('Important Senders')
    expect(sendersInput.value).toBe('boss@co.com, cto@co.com')

    const keywordsInput = screen.getByLabelText('Important Keywords')
    expect(keywordsInput.value).toBe('urgent, deadline')
  })

  it('renders with empty preferences', () => {
    render(
      <PreferencesForm
        preferences={{ important_senders: [], important_keywords: [] }}
        saving={false}
        onSave={vi.fn()}
      />
    )
    expect(screen.getByLabelText('Important Senders').value).toBe('')
  })

  it('calls onSave with parsed arrays on submit', () => {
    const onSave = vi.fn()
    render(
      <PreferencesForm preferences={mockPrefs} saving={false} onSave={onSave} />
    )

    fireEvent.change(screen.getByLabelText('Important Senders'), {
      target: { value: 'new@co.com, other@co.com' },
    })

    fireEvent.click(screen.getByText('Save Preferences'))

    expect(onSave).toHaveBeenCalledWith({
      important_senders: ['new@co.com', 'other@co.com'],
      important_keywords: ['urgent', 'deadline'],
    })
  })

  it('filters empty strings from split', () => {
    const onSave = vi.fn()
    render(
      <PreferencesForm preferences={mockPrefs} saving={false} onSave={onSave} />
    )

    fireEvent.change(screen.getByLabelText('Important Keywords'), {
      target: { value: 'urgent, , , deadline, ' },
    })

    fireEvent.click(screen.getByText('Save Preferences'))

    expect(onSave).toHaveBeenCalledWith(
      expect.objectContaining({
        important_keywords: ['urgent', 'deadline'],
      })
    )
  })

  it('shows Saving... when saving', () => {
    render(
      <PreferencesForm preferences={mockPrefs} saving={true} onSave={vi.fn()} />
    )
    const btn = screen.getByText('Saving...')
    expect(btn).toBeDisabled()
  })

  it('shows Save Preferences when not saving', () => {
    render(
      <PreferencesForm preferences={mockPrefs} saving={false} onSave={vi.fn()} />
    )
    expect(screen.getByText('Save Preferences')).not.toBeDisabled()
  })
})
