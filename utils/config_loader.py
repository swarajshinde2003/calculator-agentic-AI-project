import yaml
import os

def load_config(config_dir: str = r"F:\Git_gen_ai_project\calculator-agentic-AI-project\config"):
    config_path = os.path.join(config_dir, "config.yaml")
    config_path = os.path.abspath(config_path)

    with open(config_path, "r") as file:
        return yaml.safe_load(file)