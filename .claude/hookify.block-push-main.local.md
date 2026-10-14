---
name: block-push-main
enabled: true
event: bash
action: block
pattern: 'git\s+push\b.*\b(main|master)\b'
---
Blocked: never push to main. Push your issue-<n>-<slug> branch and open a PR.
