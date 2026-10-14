---
name: block-force-push
enabled: true
event: bash
action: block
pattern: 'git\s+push\b.*(\s-f\b|--force)'
---
Blocked: never force-push. Push a new commit instead.
