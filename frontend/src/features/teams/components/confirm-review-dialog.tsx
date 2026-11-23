import Alert from '@mui/material/Alert'
import Button from '@mui/material/Button'
import Dialog from '@mui/material/Dialog'
import DialogActions from '@mui/material/DialogActions'
import DialogContent from '@mui/material/DialogContent'
import DialogContentText from '@mui/material/DialogContentText'
import DialogTitle from '@mui/material/DialogTitle'
import type { ReviewDecision } from '@/features/teams/api/review-application'

interface ConfirmReviewDialogProps {
  open: boolean
  decision: ReviewDecision
  teamName: string
  projectTitle: string
  /** True while the request is in flight: buttons are disabled. */
  pending: boolean
  /** The backend's message if the last attempt failed. */
  error: string | null
  onConfirm: () => void
  onClose: () => void
}

const copy = {
  approve: {
    title: 'Approve this team project?',
    body: 'The team will be approved for this project.',
    button: 'Approve',
    color: 'success',
  },
  reject: {
    title: 'Reject this team project?',
    body: "The team's slot on the project will be released. This can't be undone.",
    button: 'Reject',
    color: 'error',
  },
} as const

/**
 * Asks the reviewer to confirm an approve or reject, so a stray click never
 * decides a submission. Stays open on failure to show the backend's reason.
 */
export function ConfirmReviewDialog({
  open,
  decision,
  teamName,
  projectTitle,
  pending,
  error,
  onConfirm,
  onClose,
}: ConfirmReviewDialogProps) {
  const text = copy[decision]

  return (
    <Dialog
      open={open}
      onClose={pending ? undefined : onClose}
      aria-labelledby="confirm-review-title"
      fullWidth
      maxWidth="xs"
    >
      <DialogTitle id="confirm-review-title">{text.title}</DialogTitle>
      <DialogContent>
        <DialogContentText>
          <strong>{teamName}</strong> on <strong>{projectTitle}</strong>.{' '}
          {text.body}
        </DialogContentText>
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
          color={text.color}
        >
          {pending ? 'Saving...' : text.button}
        </Button>
      </DialogActions>
    </Dialog>
  )
}
