import Alert from '@mui/material/Alert'
import Button from '@mui/material/Button'
import Dialog from '@mui/material/Dialog'
import DialogActions from '@mui/material/DialogActions'
import DialogContent from '@mui/material/DialogContent'
import DialogContentText from '@mui/material/DialogContentText'
import DialogTitle from '@mui/material/DialogTitle'
import { useId } from 'react'
import type { PendingAction } from '@/features/applications/types/application'
import { actionDescription } from '@/features/applications/utils/team-actions'

interface ConfirmActionDialogProps {
  /** The action waiting for confirmation. null closes the dialog. */
  pending: PendingAction | null
  /** True while the request is in flight. */
  isWorking: boolean
  /** The server's message if the action was rejected, else null. */
  error: string | null
  onConfirm: () => void
  onClose: () => void
}

/**
 * Asks the user to confirm an action, so a stray click during the demo can't
 * change state. A rejected action is shown here rather than in a toast, so it
 * can't be missed.
 */
export function ConfirmActionDialog({
  pending,
  isWorking,
  error,
  onConfirm,
  onClose,
}: ConfirmActionDialogProps) {
  const titleId = useId()

  return (
    <Dialog
      open={pending !== null}
      // No onClose while a request is in flight, so Esc and backdrop clicks
      // can't hide the outcome.
      onClose={isWorking ? undefined : onClose}
      aria-labelledby={titleId}
    >
      {/* `pending` is null while the dialog fades out, hence the fallbacks. */}
      <DialogTitle id={titleId}>
        {pending ? `${pending.button.label}: ${pending.projectTitle}?` : ''}
      </DialogTitle>
      <DialogContent>
        <DialogContentText>
          {pending ? actionDescription[pending.button.action] : ''}
        </DialogContentText>
        {error && (
          <Alert severity="error" sx={{ mt: 2 }}>
            {error}
          </Alert>
        )}
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose} disabled={isWorking}>
          {error ? 'Close' : 'Cancel'}
        </Button>
        {/* After a rejection, retrying the same action would just be rejected
            again, so only "Close" is offered. Disabled while working, so a
            double click can't send the action twice. */}
        {!error && (
          <Button variant="contained" onClick={onConfirm} disabled={isWorking}>
            {isWorking ? 'Working…' : 'Confirm'}
          </Button>
        )}
      </DialogActions>
    </Dialog>
  )
}
