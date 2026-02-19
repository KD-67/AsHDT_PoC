import json
import os

#    Reads module_registry.json from disk and returns its contents as a Python dictionary.
#    Called once at FastAPI startup — the result is stored in app.state.registry
#    so all subsequent requests can access it from memory without re-reading the file.

#    Raises RuntimeError (instead of letting a bare exception bubble up) so that the
#    server fails immediately and visibly if the registry is missing or broken, rather
#    than starting in a silently broken state.



def load_registry(registry_path: str) -> dict:
    # Check that the file actually exists before trying to open it. If not, ERROR
    if not os.path.exists(registry_path):
        raise RuntimeError(
            f"Module registry file not found at: {registry_path}. "
            "Ensure registry/module_registry.json exists before starting the server."
        )
    # Open and parse the JSON file. Turns it into a dict
    with open(registry_path, encoding="utf-8") as f:
        try:
            registry = json.load(f)
        # if it doesn't work, ERROR
        except json.JSONDecodeError as e:
            raise RuntimeError(
                f"Module registry file at {registry_path} is not valid JSON: {e}"
            )
    # Return the parsed dict as a plain Python dict mirroring the JSON format
    return registry