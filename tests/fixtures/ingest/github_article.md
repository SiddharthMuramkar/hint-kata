# About protected branches

Branch protection rules <a href="https://docs.github.com/en/repositories/x" class="link">enforce workflows</a>.<br>
<picture><img src="/assets/images/x.png" alt="diagram"></picture>

> [!NOTE]
> Rulesets are available on public repositories.

## Require status checks

Use `git checkout <branch>` and the inline `<br>` tag stays as code.

```yaml
on:
  push:
    branches: [main]
# <div>not html</div>
```

<div class="note">
Wrapped text stays.
</div>

<!-- hidden comment -->

## Require reviews

Reviews are required before merge.
