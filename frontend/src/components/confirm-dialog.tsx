import Alert from '@mui/material/Alert'
import Button from '@mui/material/Button'
import Dialog from '@mui/material/Dialog'
import DialogActions from '@mui/material/DialogActions'
import DialogContent from '@mui/material/DialogContent'
import DialogContentText from '@mui/material/DialogContentText'
import DialogTitle from '@mui/material/DialogTitle'
import { useId } from 'react'

interface ConfirmDialogProps {
  open: boolean
  title: string
  children: React.ReactNode
  /** Label of the confirm button, e.g. "Approve". */
  confirmLabel: string
  confirmColor?: 'primary' | 'success' | 'error'
  /** True while the request is in flight: buttons are disabled. */
  pending: boolean
  /** The backend's message if the last attempt failed. */
  error: string | null
  onConfirm: () => void
  onClose: () => void
}

/**
 * Asks the user to confirm an action, so a stray click never changes
 * anything. Stays open on failure to show the reason.
 */
export function ConfirmDialog({
  open,
  title,
  children,
  confirmLabel,
  confirmColor = 'primary',
  pending,
  error,
  onConfirm,
  onClose,
}: ConfirmDialogProps) {
  const titleId = useId()

  return (
    <Dialog
      open={open}
      onClose={pending ? undefined : onClose}
      aria-labelledby={titleId}
      fullWidth
      maxWidth="xs"
    >
      <DialogTitle id={titleId}>{title}</DialogTitle>
      <DialogContent>
        <DialogContentText>{children}</DialogContentText>
        {error && (
          <Alert severity="error" sx={{ mt: 2 }}>
            {error}
          </Alert>
        )}
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose} disabled={pending}>
          Cancel
        </Button>
        <Button
          onClick={onConfirm}
          disabled={pending}
          variant="contained"
          color={confirmColor}
        >
          {pending ? 'Saving...' : confirmLabel}
        </Button>
      </DialogActions>
    </Dialog>
  )
}
