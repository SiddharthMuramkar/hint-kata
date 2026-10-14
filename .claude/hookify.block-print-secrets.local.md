---
name: block-print-secrets
enabled: true
event: bash
action: block
pattern: '\bprintenv\b|\benv\s*(\||$)|echo\s+[\x22\x27]?\$\{?\w*(KEY|TOKEN|SECRET)'
---
Blocked: do not print environment variables or secrets.
