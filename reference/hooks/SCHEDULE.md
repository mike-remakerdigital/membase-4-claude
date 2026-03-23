# Session Scheduler

<!-- Managed by hooks/scheduler.py. Edit freely. -->
<!-- Groups processed top-to-bottom (FIFO). First group's trigger is evaluated each prompt. -->
<!-- Claude may append new groups during work. Delete groups to cancel. -->
<!-- Format: ## Group: <name> / trigger: always|session_end|after:N / keywords: ... / - [ ] prompt -->

## Group: Session Wrap-Up
trigger: session_end
keywords: wrap up, done, end session, that's all, that is all, signing off, let's stop, that's it, we're done

- [ ] Execute session wrap-up procedure: update KB, update MEMORY.md, git commit and push, generate handoff prompt for next session.
