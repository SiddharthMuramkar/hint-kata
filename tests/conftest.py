from pydantic_ai import models

models.ALLOW_MODEL_REQUESTS = False  # never hit a real LLM in tests

collect_ignore_glob = ["fixtures/*"]  # fixture task tests are run by the checker, not by us
