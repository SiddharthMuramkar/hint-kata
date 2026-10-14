"""Persona agent: the tone and length come from deps, and the token cap follows the tone.

Fill in the four TODOs.
"""

from dataclasses import dataclass

from pydantic_ai import Agent, AgentRunResult, ModelMessage, ModelSettings, RunContext  # noqa: F401
from pydantic_ai.models import Model

DEFAULT_MODEL = "openrouter:anthropic/claude-haiku-5.5"
STATIC = "You write short replies for a support desk."
TONE_TOKENS = {"brief": 150, "friendly": 300, "formal": 450}
DEFAULT_TOKENS = 300


@dataclass
class PersonaDeps:
    """What the caller decides for each run."""

    # TODO 1: add two fields:
    #   tone: str
    #   max_words: int


def settings_for(tone: str) -> ModelSettings:
    """The model settings for a tone: only `max_tokens`, taken from TONE_TOKENS."""
    # TODO 2: return ModelSettings(max_tokens=...) with the number for this tone from TONE_TOKENS.
    #   A tone that is not in the table gets DEFAULT_TOKENS.
    #   Set nothing else. In particular, never set temperature or top_p.
    raise NotImplementedError("return the settings for this tone")


def make_agent(model: Model | str | None = None) -> Agent[PersonaDeps, str]:
    """Build the agent. Tests pass a fake model; `defer_model_check` lets it build without a key."""
    agent = Agent(
        model or DEFAULT_MODEL,
        deps_type=PersonaDeps,
        instructions=STATIC,
        model_settings=ModelSettings(max_tokens=1000, timeout=20),
        defer_model_check=True,
    )

    # TODO 3: register a dynamic instructions function on `agent` with `@agent.instructions`.
    #   It takes `ctx: RunContext[PersonaDeps]` and returns one sentence or two that say
    #   which tone to use and the most words a reply may have, both read from `ctx.deps`.
    #   For example: "Use a brief tone. Keep every reply under 40 words."
    #   Leave the static `instructions=STATIC` above as it is.

    return agent


def ask(
    agent: Agent[PersonaDeps, str],
    prompt: str,
    deps: PersonaDeps,
    history: list[ModelMessage] | None = None,
) -> AgentRunResult[str]:
    """Run the agent once. The token cap follows the tone, so it is set for this run only."""
    # TODO 4: call `agent.run_sync` with `prompt`, `deps=deps`, `message_history=history`
    #   and `model_settings=settings_for(deps.tone)`. Return the result.
    raise NotImplementedError("run the agent with settings for this tone")


if __name__ == "__main__":
    # Needs OPENROUTER_API_KEY in your environment. Two small paid calls.
    agent = make_agent()
    first = ask(agent, "My invoice PDF will not open.", PersonaDeps("brief", 30))
    print(first.output)
    second = ask(
        agent, "Please say it again.", PersonaDeps("formal", 80), history=first.all_messages()
    )
    print(second.output)
