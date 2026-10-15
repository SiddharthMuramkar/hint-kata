"""A research agent with guards: a tool retry budget and run limits. Task solution."""

from dataclasses import dataclass, field

from pydantic_ai import (
    Agent,
    ModelRetry,
    RunContext,
    ToolFailed,
    UnexpectedModelBehavior,
    UsageLimitExceeded,
    UsageLimits,
)


@dataclass
class Deps:
    searches: list[str] = field(default_factory=list)  # every query the search tool ran
    fetches: list[str] = field(default_factory=list)  # every url the fetch tool was asked for


@dataclass
class Outcome:
    finished: bool  # True when the agent gave an answer
    text: str  # the answer, or "" when the run was stopped
    reason: str  # why the run was stopped, or "" when it finished


agent = Agent(
    "openai:gpt-5.2",  # real model name; the tests swap it for a FunctionModel
    deps_type=Deps,
    instructions="Answer the question. Use search and fetch if you need facts.",
    defer_model_check=True,  # do not look for an API key when this module is imported
    retries={"tools": 2},  # each tool may send the model two retry prompts, not just one
)

# A run may take at most 5 model turns and run at most 3 tools successfully.
LIMITS = UsageLimits(request_limit=5, tool_calls_limit=3)


@agent.tool
def search(ctx: RunContext[Deps], query: str) -> str:
    """Search the docs. This stand-in always works, and never finds a final answer."""
    ctx.deps.searches.append(query)
    return "Some results. Try a more specific query."


@agent.tool
def fetch(ctx: RunContext[Deps], url: str) -> str:
    """Fetch a web page. This stand-in rejects bad urls and has one host that is always down."""
    ctx.deps.fetches.append(url)
    if not url.startswith("https://"):
        raise ModelRetry("Use a full https:// URL.")
    if "down.example" in url:
        raise ToolFailed("The site is down.")
    return "Page text."


def run_guarded(prompt: str, deps: Deps) -> Outcome:
    """Run the agent under LIMITS. A run that is stopped gives an Outcome, not an exception."""
    try:
        result = agent.run_sync(prompt, deps=deps, usage_limits=LIMITS)
    except (UsageLimitExceeded, UnexpectedModelBehavior) as exc:
        return Outcome(finished=False, text="", reason=str(exc))
    return Outcome(finished=True, text=result.output, reason="")
