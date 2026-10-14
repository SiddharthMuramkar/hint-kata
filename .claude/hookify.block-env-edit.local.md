---
name: block-env-edit
enabled: true
event: file
action: block
conditions:
  - field: file_path
    operator: regex_match
    pattern: '\.env($|\.(?!example))'
---
Blocked: do not edit .env files. The owner types secret values. Edit .env.example for new variable names.
