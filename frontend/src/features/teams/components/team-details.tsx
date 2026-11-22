import Card from '@mui/material/Card'
import CardContent from '@mui/material/CardContent'
import List from '@mui/material/List'
import ListItem from '@mui/material/ListItem'
import ListItemText from '@mui/material/ListItemText'
import Typography from '@mui/material/Typography'
import { fullName } from '@/lib/utils/full-name'
import type { components } from '@/types/api'

type Team = components['schemas']['TeamRead']

interface TeamDetailsProps {
  team: Team
  /** The signed-in student, marked "(you)" in the member list. */
  studentId: string
}

/** A team's name and its members. */
export function TeamDetails({ team, studentId }: TeamDetailsProps) {
  return (
    <Card variant="outlined">
      <CardContent>
        <Typography variant="h6" component="h2">
          {team.name}
        </Typography>
        <List dense>
          {team.members.map(({ user, student_number }) => (
            <ListItem key={user.id} disableGutters>
              <ListItemText
                primary={`${fullName(user)}${user.id === studentId ? ' (you)' : ''}`}
                secondary={`${user.email}${student_number ? ` · ${student_number}` : ''}`}
              />
            </ListItem>
          ))}
        </List>
      </CardContent>
    </Card>
  )
}
