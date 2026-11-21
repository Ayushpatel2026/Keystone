"""Write the API's OpenAPI schema to a file, without running the server.

The frontend generates its TypeScript API types from this file:

    uv run python -m app.export_openapi <output path>
"""

import json
import os
import sys
from pathlib import Path


def main() -> None:
    if len(sys.argv) != 2:
        sys.exit("usage: python -m app.export_openapi <output path>")

    # Building the app creates a database engine, which needs a well-formed URL.
    # It never connects here, so a placeholder works when no .env is set up.
    os.environ.setdefault(
        "KEYSTONE_DATABASE_URL", "postgresql+asyncpg://openapi:openapi@localhost/openapi"
    )

    # Imported after the env var is set, because importing builds the app.
    from app.main import app

    output = Path(sys.argv[1])
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(app.openapi(), indent=2) + "\n", encoding="utf-8")
    print(f"Wrote OpenAPI schema to {output}")


if __name__ == "__main__":
    main()
