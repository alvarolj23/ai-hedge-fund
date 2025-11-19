---
applyTo: '**'
---

# Documentation standards

Keep documentation minimal, focused, and actionable. Documentation should enable an end user or developer to follow a process completely when it matters: feature delivery, handoff, or important architecture/configuration changes. Do not produce full documentation for every small change.

# When to generate or update documentation (required)
Generate or update docs only for:
- Implementing a new feature or public API that others will use.
- Creating a plan, design, or runbook that others must follow to implement or operate something.
- Implementing significant architectural, configuration, deployment, or security changes.
- Preparing a public release, demo, or handoff to another team.

Do not generate docs for:
- Minor bugfixes that do not change user/developer workflows.
- Internal refactors with no external/operational impact.
- Experimental changes that are not being promoted to mainline.
- Creating documentation (Markdown) files for each small fix or for individual test-failure analyses — only create documentation/MD files for larger components or significant changes.

# Documentation guidelines
- Use README.md as the primary documentation file.
- Include only essential, testable steps for setup, installation, usage, and any required commands.
- Provide clear prerequisites and exact commands (activate venv, install deps, run tests).
- For significant features include: short summary, how to use, configuration changes (if any), and verification steps.
- For plans/designs include: objectives, required steps, owners, and acceptance criteria.
- Update documentation promptly for significant changes. For minor changes, batch updates into the next release or documentation sprint.
- Avoid proliferating multiple markdown files; consolidate where practical.
- Test documentation by following it as a new user before merging.

# Style
- Keep content concise and actionable.
- Prefer concrete examples and commands over prose.
- Link to deeper design docs only when necessary.
