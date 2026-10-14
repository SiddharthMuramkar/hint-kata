---
name: block-print-secrets
enabled: true
event: bash
action: block
pattern: '\b(printenv|env)\s*$|echo\s+\$\{?\w*(KEY|TOKEN|SECRET)'
---
Blocked: do not print environment variables or secrets.
