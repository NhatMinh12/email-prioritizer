import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { Pagination } from '../Pagination'

describe('Pagination', () => {
  it('renders nothing when total fits in one page', () => {
    const { container } = render(
      <Pagination page={1} pageSize={20} total={15} onPageChange={vi.fn()} />
    )
    expect(container.firstChild).toBeNull()
  })

  it('renders page info', () => {
    render(
      <Pagination page={1} pageSize={20} total={50} onPageChange={vi.fn()} />
    )
    expect(screen.getByText(/1–20/)).toBeInTheDocument()
    expect(screen.getByText(/of 50/)).toBeInTheDocument()
  })

  it('shows correct range for middle page', () => {
    render(
      <Pagination page={2} pageSize={20} total={50} onPageChange={vi.fn()} />
    )
    expect(screen.getByText(/21–40/)).toBeInTheDocument()
  })

  it('caps range at total for last page', () => {
    render(
      <Pagination page={3} pageSize={20} total={50} onPageChange={vi.fn()} />
    )
    expect(screen.getByText(/41–50/)).toBeInTheDocument()
  })

  it('shows page X / Y', () => {
    render(
      <Pagination page={2} pageSize={20} total={50} onPageChange={vi.fn()} />
    )
    expect(screen.getByText('2 / 3')).toBeInTheDocument()
  })

  it('disables Previous on first page', () => {
    render(
      <Pagination page={1} pageSize={20} total={50} onPageChange={vi.fn()} />
    )
    expect(screen.getByText('Previous')).toBeDisabled()
  })

  it('disables Next on last page', () => {
    render(
      <Pagination page={3} pageSize={20} total={50} onPageChange={vi.fn()} />
    )
    expect(screen.getByText('Next')).toBeDisabled()
  })

  it('calls onPageChange with previous page', () => {
    const onChange = vi.fn()
    render(
      <Pagination page={2} pageSize={20} total={50} onPageChange={onChange} />
    )
    fireEvent.click(screen.getByText('Previous'))
    expect(onChange).toHaveBeenCalledWith(1)
  })

  it('calls onPageChange with next page', () => {
    const onChange = vi.fn()
    render(
      <Pagination page={1} pageSize={20} total={50} onPageChange={onChange} />
    )
    fireEvent.click(screen.getByText('Next'))
    expect(onChange).toHaveBeenCalledWith(2)
  })
})
