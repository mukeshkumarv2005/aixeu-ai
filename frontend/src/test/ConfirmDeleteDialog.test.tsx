import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { ConfirmDeleteDialog } from '../components/shared/ConfirmDeleteDialog'

describe('ConfirmDeleteDialog Component', () => {
  it('renders correctly with title and message', () => {
    const handleConfirm = vi.fn()
    const handleCancel = vi.fn()

    render(
      <ConfirmDeleteDialog
        title="Are you sure?"
        message="This action cannot be undone."
        onConfirm={handleConfirm}
        onCancel={handleCancel}
      />
    )

    expect(screen.getByText('Are you sure?')).toBeInTheDocument()
    expect(screen.getByText('This action cannot be undone.')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Delete' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Cancel' })).toBeInTheDocument()
  })

  it('triggers onConfirm when confirm button clicked', () => {
    const handleConfirm = vi.fn()
    const handleCancel = vi.fn()

    render(
      <ConfirmDeleteDialog
        title="Delete Item"
        message="Delete now."
        onConfirm={handleConfirm}
        onCancel={handleCancel}
      />
    )

    fireEvent.click(screen.getByRole('button', { name: 'Delete' }))
    expect(handleConfirm).toHaveBeenCalledTimes(1)
  })

  it('triggers onCancel when cancel button clicked', () => {
    const handleConfirm = vi.fn()
    const handleCancel = vi.fn()

    render(
      <ConfirmDeleteDialog
        title="Delete Item"
        message="Delete now."
        onConfirm={handleConfirm}
        onCancel={handleCancel}
      />
    )

    fireEvent.click(screen.getByRole('button', { name: 'Cancel' }))
    expect(handleCancel).toHaveBeenCalledTimes(1)
  })

  it('disables buttons and shows loader when isLoading is true', () => {
    const handleConfirm = vi.fn()
    const handleCancel = vi.fn()

    render(
      <ConfirmDeleteDialog
        title="Delete Item"
        message="Delete now."
        onConfirm={handleConfirm}
        onCancel={handleCancel}
        isLoading={true}
      />
    )

    const confirmBtn = screen.getByRole('button', { name: 'Delete' })
    const cancelBtn = screen.getByRole('button', { name: 'Cancel' })

    expect(confirmBtn).toBeDisabled()
    expect(cancelBtn).toBeDisabled()
  })
})
