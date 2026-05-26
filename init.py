from pathlib import Path
import sys

ROOT_DIR = Path(__file__).resolve().parent
SRC_DIR = ROOT_DIR / "src"

if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from sst_chatbot.config import require_env  # noqa: E402
from sst_chatbot.config import validate_runtime_imports  # noqa: E402


def main() -> None:
    require_env(("OPENAI_API_KEY", "LANGCHAIN_API_KEY"))
    validate_runtime_imports()
    print("Configuracion completada y validada con exito.")


if __name__ == "__main__":
    main()
