import HubRoundedIcon from '@mui/icons-material/HubRounded'
import Box from '@mui/material/Box'
import Stack from '@mui/material/Stack'
import Typography from '@mui/material/Typography'

/** The Keystone logo and name. Adapted from the template's CustomIcon. */
export function BrandMark() {
  return (
    <Stack direction="row" spacing={1} sx={{ alignItems: 'center' }}>
      <Box
        aria-hidden
        sx={{
          width: '1.75rem',
          height: '1.75rem',
          borderRadius: '999px',
          display: 'flex',
          justifyContent: 'center',
          alignItems: 'center',
          backgroundImage:
            'linear-gradient(135deg, hsl(210, 98%, 60%) 0%, hsl(210, 100%, 35%) 100%)',
          color: 'hsla(210, 100%, 95%, 0.9)',
          border: '1px solid',
          borderColor: 'hsl(210, 100%, 55%)',
          boxShadow: 'inset 0 2px 5px rgba(255, 255, 255, 0.3)',
        }}
      >
        <HubRoundedIcon color="inherit" sx={{ fontSize: '1.1rem' }} />
      </Box>
      <Typography
        variant="h6"
        component="span"
        sx={{ color: 'text.primary', fontWeight: 700 }}
      >
        Keystone
      </Typography>
    </Stack>
  )
}
