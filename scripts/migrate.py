"""Apply app/pg_schema.sql to Postgres (Neon). Run: uv run python scripts/migrate.py"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # so `app` imports from scripts/

from app.config import settings  # noqa: E402
from app.store_pg import apply_schema  # noqa: E402


def main() -> None:
    url = settings.database_url_unpooled
    if not url:
        raise SystemExit("Set DATABASE_URL_UNPOOLED in the local env file first.")
    print(f"schema version {apply_schema(url)}")


if __name__ == "__main__":
    main()
