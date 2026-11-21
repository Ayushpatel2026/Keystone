import PersonOffRoundedIcon from '@mui/icons-material/PersonOffRounded'
import Avatar from '@mui/material/Avatar'
import ListItemAvatar from '@mui/material/ListItemAvatar'
import ListItemText from '@mui/material/ListItemText'
import ListSubheader from '@mui/material/ListSubheader'
import MenuItem from '@mui/material/MenuItem'
import Select, { selectClasses } from '@mui/material/Select'
import Stack from '@mui/material/Stack'
import Typography from '@mui/material/Typography'
import { useEffect, useId } from 'react'
import { useActingAs, useSwitchUser, useUsers } from '@/lib/auth'
import { updateActingAs, type DemoUser } from '@/lib/auth'

const NOBODY = ''

const roleGroups: { role: DemoUser['role']; label: string; single: string }[] =
  [
    { role: 'student', label: 'Students', single: 'Student' },
    { role: 'supervisor', label: 'Supervisors', single: 'Supervisor' },
    { role: 'instructor', label: 'Instructors', single: 'Instructor' },
    { role: 'ta', label: 'TAs', single: 'TA' },
  ]

function roleName(role: DemoUser['role']) {
  return roleGroups.find((group) => group.role === role)?.single ?? role
}

function fullName(user: DemoUser) {
  return `${user.first_name} ${user.last_name}`
}

function UserAvatar({ user }: { user: DemoUser | null }) {
  return (
    <Avatar
      alt=""
      sx={{ width: 28, height: 28, fontSize: '0.8rem', fontWeight: 600 }}
    >
      {user ? (
        `${user.first_name[0] ?? ''}${user.last_name[0] ?? ''}`
      ) : (
        <PersonOffRoundedIcon fontSize="small" />
      )}
    </Avatar>
  )
}

/**
 * Pick who the app acts as (#235). The PoC has no real sign-in: picking a user
 * signs in as them with the seed password, and every API request then carries
 * their token. Adapted from the template's SelectContent.
 */
export function UserSwitcher() {
  const labelId = useId()
  const errorId = useId()
  const actingAs = useActingAs()
  const users = useUsers()
  const switchUser = useSwitchUser()

  // After a reseed the stored user may have a new id (same email) or be gone.
  useEffect(() => {
    if (!actingAs || !users.data) return
    const match = users.data.find((user) => user.email === actingAs.email)
    if (!match) switchUser.mutate(null)
    else if (match.id !== actingAs.id) updateActingAs(match)
    // switchUser changes every render; only re-check when the data changes.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [actingAs, users.data])

  // Until the list loads (or if it fails), offer just the remembered user, so
  // the Select always has an option matching its value.
  const choices = users.data ?? (actingAs ? [actingAs] : [])
  const usersById = new Map(choices.map((user) => [user.id, user]))
  const value = actingAs && usersById.has(actingAs.id) ? actingAs.id : NOBODY

  const options = roleGroups.flatMap(({ role, label }) => {
    const group = choices.filter((user) => user.role === role)
    if (group.length === 0) return []
    // Select needs its items as direct children, so no fragments here.
    return [
      <ListSubheader key={`header-${role}`}>{label}</ListSubheader>,
      ...group.map((user) => (
        <MenuItem key={user.id} value={user.id}>
          <ListItemAvatar sx={{ minWidth: 40 }}>
            <UserAvatar user={user} />
          </ListItemAvatar>
          <ListItemText primary={fullName(user)} secondary={user.email} />
        </MenuItem>
      )),
    ]
  })

  let message: string | null = null
  if (switchUser.isError) {
    message = `${switchUser.error.message}`
  } else if (users.isError) {
    message = 'Failed to load users.'
  }

  return (
    <Stack
      sx={{ p: 2, gap: 1, borderTop: '1px solid', borderColor: 'divider' }}
    >
      <Typography
        id={labelId}
        variant="caption"
        sx={{ color: 'text.secondary', fontWeight: 500 }}
      >
        Acting as:
      </Typography>
      <Select
        labelId={labelId}
        SelectDisplayProps={{
          'aria-describedby': message ? errorId : undefined,
        }}
        value={value}
        displayEmpty
        fullWidth
        disabled={users.isPending || switchUser.isPending}
        onChange={(event) => {
          const id = event.target.value
          switchUser.mutate(id === NOBODY ? null : (usersById.get(id) ?? null))
        }}
        renderValue={(id) => {
          const user = usersById.get(id) ?? null
          return (
            <Stack
              direction="row"
              sx={{ gap: 1, alignItems: 'center', minWidth: 0 }}
            >
              <UserAvatar user={user} />
              <Stack sx={{ minWidth: 0 }}>
                <Typography variant="body2" noWrap sx={{ fontWeight: 500 }}>
                  {user ? fullName(user) : 'Nobody'}
                </Typography>
                <Typography
                  variant="caption"
                  noWrap
                  sx={{ color: 'text.secondary', lineHeight: 1.2 }}
                >
                  {user
                    ? roleName(user.role)
                    : users.isPending
                      ? 'Loading users…'
                      : 'Pick a user'}
                </Typography>
              </Stack>
            </Stack>
          )
        }}
        MenuProps={{ slotProps: { paper: { sx: { maxHeight: 420 } } } }}
        sx={{
          minHeight: 48,
          [`& .${selectClasses.select}`]: { py: 0.75, pl: 1 },
        }}
      >
        <MenuItem value={NOBODY}>
          <ListItemAvatar sx={{ minWidth: 40 }}>
            <UserAvatar user={null} />
          </ListItemAvatar>
          <ListItemText primary="Nobody" secondary="Signed out" />
        </MenuItem>
        {options}
      </Select>
      {message && (
        <Typography
          id={errorId}
          role="alert"
          variant="caption"
          sx={{ color: 'error.main' }}
        >
          {message}
        </Typography>
      )}
    </Stack>
  )
}
