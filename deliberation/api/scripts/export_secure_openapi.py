import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.secure_backend.main import create_app


def main() -> None:
    app = create_app()
    output_path = Path(__file__).resolve().parents[1] / "openapi" / "secure_backend.openapi.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(app.openapi(), indent=2), encoding="utf-8")
    print(f"Wrote OpenAPI spec to {output_path}")


if __name__ == "__main__":
    main()

