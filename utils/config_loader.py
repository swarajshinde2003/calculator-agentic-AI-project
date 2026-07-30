import yaml
import os

# Resolve config relative to this file so the project is path-portable.
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def load_config():
    config_path = os.path.join(_PROJECT_ROOT, "config", "config.yaml")
    with open(config_path, "r") as file:
        return yaml.safe_load(file)