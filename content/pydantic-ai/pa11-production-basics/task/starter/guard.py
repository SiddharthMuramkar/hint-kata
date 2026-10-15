"""Task: add the guards. A research agent that can loop must be stopped by its limits."""

from dataclasses import dataclass, field

from pydantic_ai import (
    Agent,
    ModelRetry,
    RunContext,
    ToolFailed,
    UnexpectedModelBehavior,  # noqa: F401  (you will use these)
    UsageLimitExceeded,  # noqa: F401
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


# TODO 1: give each tool a retry budget of 2 (the default is 1). Add one argument to the Agent.
agent = Agent(
    "openai:gpt-5.2",  # real model name; the tests swap it for a FunctionModel
    deps_type=Deps,
    instructions="Answer the question. Use search and fetch if you need facts.",
    defer_model_check=True,  # do not look for an API key when this module is imported
)

# TODO 2: stop a run after at most 5 model turns (request_limit) and at most 3 tool calls that
# succeed (tool_calls_limit). This line uses the defaults, which are far too generous.
LIMITS = UsageLimits()


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
    # TODO 3: run the agent under LIMITS (the `usage_limits` argument). If the run is stopped
    # because a limit or a retry budget is used up, return
    # Outcome(finished=False, text="", reason=str(the exception)) instead of raising.
    # If the agent answers, return Outcome(finished=True, text=<the answer>, reason="").
    result = agent.run_sync(prompt, deps=deps)
    return Outcome(finished=True, text=result.output, reason="")
