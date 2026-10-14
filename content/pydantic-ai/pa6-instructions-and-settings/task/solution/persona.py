"""Persona agent: the tone and length come from deps, and the token cap follows the tone."""

from dataclasses import dataclass

from pydantic_ai import Agent, AgentRunResult, ModelMessage, ModelSettings, RunContext
from pydantic_ai.models import Model

DEFAULT_MODEL = "openrouter:anthropic/claude-haiku-5.5"
STATIC = "You write short replies for a support desk."
TONE_TOKENS = {"brief": 150, "friendly": 300, "formal": 450}
DEFAULT_TOKENS = 300


@dataclass
class PersonaDeps:
    """What the caller decides for each run."""

    tone: str
    max_words: int


def settings_for(tone: str) -> ModelSettings:
    """The model settings for a tone: only `max_tokens`, taken from TONE_TOKENS."""
    return ModelSettings(max_tokens=TONE_TOKENS.get(tone, DEFAULT_TOKENS))


def make_agent(model: Model | str | None = None) -> Agent[PersonaDeps, str]:
    """Build the agent. Tests pass a fake model; `defer_model_check` lets it build without a key."""
    agent = Agent(
        model or DEFAULT_MODEL,
        deps_type=PersonaDeps,
        instructions=STATIC,
        model_settings=ModelSettings(max_tokens=1000, timeout=20),
        defer_model_check=True,
    )

    @agent.instructions
    def persona(ctx: RunContext[PersonaDeps]) -> str:
        return f"Use a {ctx.deps.tone} tone. Keep every reply under {ctx.deps.max_words} words."

    return agent


def ask(
    agent: Agent[PersonaDeps, str],
    prompt: str,
    deps: PersonaDeps,
    history: list[ModelMessage] | None = None,
) -> AgentRunResult[str]:
    """Run the agent once. The token cap follows the tone, so it is set for this run only."""
    return agent.run_sync(
        prompt,
        deps=deps,
        message_history=history,
        model_settings=settings_for(deps.tone),
    )


if __name__ == "__main__":
    # Needs OPENROUTER_API_KEY in your environment. Two small paid calls.
    agent = make_agent()
    first = ask(agent, "My invoice PDF will not open.", PersonaDeps("brief", 30))
    print(first.output)
    second = ask(
        agent, "Please say it again.", PersonaDeps("formal", 80), history=first.all_messages()
    )
    print(second.output)
