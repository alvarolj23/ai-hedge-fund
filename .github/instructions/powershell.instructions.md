---
applyTo: '**/*.ps1'
---

# Azure CLI standards.

I need to always use PowerShell on my Windows laptop. I can't use Azure CLI with Bash.

# PowerShell execution preferences

- Run commands in Windows PowerShell 5.1 (not PowerShell Core).
- When chaining commands on a single line, separate them with `;` instead of `&&`.
- Use PowerShell line continuations with the backtick character `` ` `` for multi-line Azure CLI commands.
- Avoid Bash-specific environment syntax (for example `export`, `$VAR=value`, command substitution).
- If Azure CLI streaming output misbehaves, invoke the command via `cmd /c` from PowerShell to keep logs readable.
- Feel free to execute the powershell azure cli commands that you need