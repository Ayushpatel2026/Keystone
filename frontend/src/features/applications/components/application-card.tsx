import Button from '@mui/material/Button'
import Card from '@mui/material/Card'
import CardContent from '@mui/material/CardContent'
import Chip from '@mui/material/Chip'
import Stack from '@mui/material/Stack'
import Typography from '@mui/material/Typography'
import type {
  Application,
  TeamAction,
} from '@/features/applications/types/application'
import {
  statusChipColor,
  statusInfo,
} from '@/features/applications/utils/application-status'
import { actionsByStatus } from '@/features/applications/utils/team-actions'

interface ApplicationCardProps {
  application: Application
  projectTitle: string
  supervisorName: string
  /** Ready-to-show capacity text, e.g. "1 of 2 slots reserved (open)". */
  capacity: string
  /** Called when the user clicks one of the status's action buttons. */
  onAction: (button: TeamAction) => void
}

/** One application: its project, status, and the actions the team may take. */
export function ApplicationCard({
  application,
  projectTitle,
  supervisorName,
  capacity,
  onAction,
}: ApplicationCardProps) {
  const { label, closed } = statusInfo[application.status]
  const chipColor = statusChipColor(application.status)
  const buttons = actionsByStatus[application.status]

  return (
    <Card
      variant="outlined"
      // Closed: grey fill, dashed border, muted text. Open: coloured border.
      sx={
        closed
          ? {
              bgcolor: 'action.hover',
              borderStyle: 'dashed',
              color: 'text.secondary',
            }
          : {
              borderColor:
                chipColor === 'success' ? 'success.main' : 'primary.main',
            }
      }
    >
      <CardContent>
        <Stack
          direction="row"
          sx={{ justifyContent: 'space-between', alignItems: 'start', gap: 2 }}
        >
          <Typography variant="h6" component="h3">
            {projectTitle}
          </Typography>
          <Chip label={label} color={chipColor} size="small" />
        </Stack>
        <Typography variant="body2">Supervisor: {supervisorName}</Typography>
        <Typography variant="body2">Capacity: {capacity}</Typography>
        {/* Timestamp (SRS FR_DisplayTimestamps). It also shows how stale a view is. */}
        <Typography variant="caption">
          Updated {new Date(application.updated_at).toLocaleString()}
        </Typography>

        {buttons.length > 0 && (
          <Stack direction="row" spacing={1} sx={{ mt: 2 }}>
            {buttons.map((button) => (
              <Button
                // Keyed by label: Decline and Withdraw share an action name but
                // are never shown together.
                key={button.label}
                variant={
                  button.action === 'withdraw' ? 'outlined' : 'contained'
                }
                color={button.action === 'withdraw' ? 'error' : 'primary'}
                onClick={() => {
                  onAction(button)
                }}
              >
                {button.label}
              </Button>
            ))}
          </Stack>
        )}
      </CardContent>
    </Card>
  )
}
