---
name: block-rm-rf
enabled: true
event: bash
action: block
pattern: 'rm\s+-[a-zA-Z]*r[a-zA-Z]*f|rm\s+-[a-zA-Z]*f[a-zA-Z]*r'
---
Blocked: rm -rf is not allowed. Delete specific files, or ask the owner.
