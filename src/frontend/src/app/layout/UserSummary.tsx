import PersonRoundedIcon from '@mui/icons-material/PersonRounded'
import Avatar from '@mui/material/Avatar'
import Box from '@mui/material/Box'
import Stack from '@mui/material/Stack'
import Typography from '@mui/material/Typography'

/**
 * Who the app is acting as, shown at the bottom of the side menu.
 *
 * Placeholder until the demo user switcher (#235) replaces it.
 */
export function UserSummary() {
  return (
    <Stack
      direction="row"
      sx={{
        p: 2,
        gap: 1,
        alignItems: 'center',
        borderTop: '1px solid',
        borderColor: 'divider',
      }}
    >
      <Avatar sx={{ width: 36, height: 36 }}>
        <PersonRoundedIcon />
      </Avatar>
      <Box sx={{ minWidth: 0 }}>
        <Typography variant="body2" sx={{ fontWeight: 500 }}>
          No user selected
        </Typography>
        <Typography variant="caption" sx={{ color: 'text.secondary' }}>
          User switcher coming in #235
        </Typography>
      </Box>
    </Stack>
  )
}
