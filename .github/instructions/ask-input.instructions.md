---
applyTo: '**'
---

# Critical decision-making standards.

Always seek user input before making critical decisions that could significantly impact the application's architecture, data, or functionality. If the user's request is ambiguous, ask a clarifying question before proceeding.

# When to ask for user input

- Before modifying database schema or migration strategies
- Before choosing between multiple architectural patterns or agent implementations
- Before selecting data storage formats (CSV vs Parquet vs other)
- Before changing core dependencies or frameworks
- Before implementing security-sensitive changes
- Before refactoring critical system components (orchestrator, agents, database connectors)
- Before modifying configuration structures that affect multiple components

# When to present multiple options vs a single plan

- If the user asks for a "plan" or "implementation", produce a single clear, structured plan by default.
- Present multiple options (2–4) only when:
    - The decision is critical (see "When to ask for user input"), or
    - The user explicitly requests alternatives, or
    - The prompt lacks necessary context and multiple viable approaches exist.
- If multiple options are presented, label them clearly (A, B, C, etc.), mark the recommended option, and give 1–2 sentence trade-offs for each.

# How to present options (only for critical decisions or when requested)

- Present 2–4 concrete options labeled clearly (A, B, C, etc.).
- Mark the recommended option explicitly: **A (recommended)**, B, C
- Briefly explain the trade-offs for each option (1–2 sentences max)
- State why the recommended option is preferred
- Wait for explicit user choice before proceeding

# Example format (use only when presenting options)

