---
name: block-push-main
enabled: true
event: bash
action: block
pattern: 'git\s+push\b.*(\s|:)(main|master)(\s|$)'
---
Blocked: never push to main. Push your issue-<n>-<slug> branch and open a PR.
