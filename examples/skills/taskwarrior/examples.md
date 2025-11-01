# Taskwarrior Examples

## Quick Start Examples

### Daily Workflow

```bash
# Morning: See what's on your plate
task next

# Add today's tasks
task add "Review pull requests" project:work priority:H due:today +code-review
task add "Team standup at 10am" due:today +meeting
task add "Update documentation" project:work due:eod

# Start working on a task
task 5 start

# Complete a task
task 5 done

# End of day: See what's left
task list
```

### Project Management

```bash
# Set up a work context
task context define work project:work
task context work

# Add project tasks
task add "Design API endpoints" project:api-rewrite priority:H
task add "Write unit tests" project:api-rewrite depends:1
task add "Update API docs" project:api-rewrite depends:2

# View project status
task project:api-rewrite list
task project:api-rewrite burndown
```

### GTD (Getting Things Done) Style

```bash
# Inbox processing
task add "Research new framework"
task add "Call dentist"
task add "Buy groceries"

# Organize with tags and projects
task 1 modify project:research +work priority:M
task 2 modify +personal +phone due:today
task 3 modify +personal +errands

# Weekly review
task all
task project:work list
task +personal list
```

### Recurring Tasks

```bash
# Daily standup
task add "Daily standup" due:tomorrow recur:daily until:eom +meeting

# Weekly report
task add "Submit weekly report" due:friday recur:weekly +report

# Monthly review
task add "Monthly team review" due:eom recur:monthly +meeting
```

### Complex Filters

```bash
# High priority work tasks due this week
task project:work priority:H due.before:eow list

# All urgent tasks not in waiting state
task +urgent status:pending list

# Tasks I'm blocked on
task status:waiting list

# Overdue tasks
task +OVERDUE list

# Tasks modified in the last 2 days
task modified.after:today-2days list
```

### Tags Organization

```bash
# Common tag patterns
+bug          # Bug fixes
+feature      # New features
+urgent       # Urgent items
+meeting      # Meetings
+review       # Code reviews
+research     # Research tasks
+blocked      # Blocked tasks
+waiting      # Waiting on someone else
+someday      # Someday/maybe tasks

# Add multiple tags
task add "Fix critical login issue" +bug +urgent +security priority:H

# Search by tag
task +bug list
task +urgent list
```

### Time Tracking

```bash
# Start working on a task
task 5 start

# Check what you're working on
task +ACTIVE list

# Stop working
task 5 stop

# See time spent
task 5 info
```

### Reporting

```bash
# Summary of all tasks
task summary

# Burndown chart
task burndown.daily
task burndown.weekly

# Completed tasks this week
task end.after:sow completed list

# Statistics
task stats

# Custom report: high priority work tasks
task project:work priority:H list
```

## Pro Tips

1. **Use abbreviations**: `task add` can be shortened to `task add`
2. **Tab completion**: Enable shell completion for faster typing
3. **Aliases**: Create shell aliases for common commands
4. **Sync**: Use taskwarrior sync to sync across devices
5. **Custom reports**: Configure custom reports in ~/.taskrc
