---
name: block-sudo
enabled: true
event: bash
action: block
pattern: '(^|[;&|]\s*)sudo\s'
---
Blocked: sudo is not allowed. Ask the owner to run it.
