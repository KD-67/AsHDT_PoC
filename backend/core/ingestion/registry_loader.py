import json
import os


def load_registry(registry_path: str) -> dict:
    """
    Reads module_registry.json from disk and returns its contents as a Python dictionary.
    Called once at FastAPI startup — the result is stored in app.state.registry
    so all subsequent requests can access it from memory without re-reading the file.

    Raises RuntimeError (instead of letting a bare exception bubble up) so that the
    server fails immediately and visibly if the registry is missing or broken, rather
    than starting in a silently broken state.
    """

    # Check that the file actually exists before trying to open it.
    # os.path.exists() returns False for both missing files and missing directories,
    # so this covers the case where the registry/ folder itself was deleted.
    if not os.path.exists(registry_path):
        raise RuntimeError(
            f"Module registry file not found at: {registry_path}. "
            "Ensure registry/module_registry.json exists before starting the server."
        )

    # Open and parse the JSON file.
    # 'encoding="utf-8"' is explicit best practice — avoids surprises on Windows
    # where the default encoding can vary by system locale.
    with open(registry_path, encoding="utf-8") as f:
        try:
            registry = json.load(f)
        except json.JSONDecodeError as e:
            # json.JSONDecodeError tells us exactly where in the file the problem is.
            # We re-raise as RuntimeError so the caller only needs to catch one type.
            raise RuntimeError(
                f"Module registry file at {registry_path} is not valid JSON: {e}"
            )

    # Return the parsed dict. At this point it is a plain Python dict mirroring the
    # JSON structure: { "registry_version": "1.0", "modules": [ ... ] }
    return registry