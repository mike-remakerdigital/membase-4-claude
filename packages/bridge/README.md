# Bridge Package

This package is reserved for reusable bridge runtime, launchers, and installers.

Current v1 state:

- the generated project includes a bridge contract and `.mcp.project.json`
- the transport itself is still project-configured

That means `membase-4-claude` now bootstraps the communication contract, but not yet a universal transport implementation.
