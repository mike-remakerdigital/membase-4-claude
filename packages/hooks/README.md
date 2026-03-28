# Hooks Package

This package owns reusable hook behavior for generated Membase projects.

Current v1 delivery model:

- generated hook files are scaffolded by `packages.platform.scaffold`
- the first shipped hooks are:
  - SessionStart assertion + handoff injection
  - UserPromptSubmit specification classifier

Later milestones can extract those into importable shared modules, but v1 already treats them as managed platform assets instead of ad hoc copy-paste instructions.
