from pydantic_ai import models

models.ALLOW_MODEL_REQUESTS = False  # never hit a real LLM in tests
