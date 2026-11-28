"""Run the local browser interface."""

import os

from ai_quiz_generator.ai.provider import AIProviderConfigurationError
from ai_quiz_generator.web.app import create_app


def main() -> int:
    try:
        app = create_app()
    except AIProviderConfigurationError as exc:
        print(f"Could not start browser interface: {exc}")
        return 1

    port = int(os.environ.get("QUIZ_WEB_PORT", "5000"))
    print(f"Open http://127.0.0.1:{port} in your browser.")
    app.run(host="127.0.0.1", port=port, debug=False)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
