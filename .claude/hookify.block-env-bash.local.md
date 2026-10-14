---
name: block-env-bash
enabled: true
event: bash
action: block
pattern: '(cat|head|tail|less|more|sed|grep|source|\.)\s+[^|;]*\.env(?!\.example)(\.[a-z]+)?\b'
---
Blocked: do not read .env from the shell. Only the owner reads secrets. .env.example is fine.
