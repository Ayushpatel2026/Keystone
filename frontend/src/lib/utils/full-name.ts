/** "First Last" for any user-like object (a DemoUser, a team member, ...). */
export function fullName(user: { first_name: string; last_name: string }) {
  return `${user.first_name} ${user.last_name}`
}
