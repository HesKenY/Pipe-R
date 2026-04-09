# Log Directory

Runtime logs for the Pipe-R workspace are written here so the repo stays cleaner and the current checkpoint is easy to find.

## Files
- `hub.log` - terminal / command deck activity
- `server.log` - HTTP server activity

## Notes
- These logs are runtime artifacts and are ignored by git.
- Keep a short summary of meaningful checkpoints in `.claude/SESSION_LOG.md` instead of relying on raw log history.
