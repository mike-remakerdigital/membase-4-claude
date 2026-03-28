# Versioning Policy

Membase uses semantic versions.

## Major

Increment the major version when a release introduces breaking manifest, template, or migration behavior.

## Minor

Increment the minor version when a release adds new modules or new bootstrap capabilities without breaking existing consumers.

## Patch

Increment the patch version when a release fixes defects in the existing managed infrastructure or documentation.

## Upgrade expectation

Generated projects should record the platform version in `membase.project.json`.
The manifest should also record the managed KB location so future update flows can
refresh the runtime without touching project-owned content.

Future `membase update` and `membase migrate` flows will use that version to determine safe upgrade paths and required migrations.
