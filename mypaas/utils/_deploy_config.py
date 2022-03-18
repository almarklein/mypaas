"""
Reads the deploy configuration from mypaas.toml file.
"""
import os
import toml

default_config = {
    "ignore": ["__pycache__", "htmlcov", ".git", "node_modules"]
}

def deploy_config(pwd):
    config = default_config
    try:
        path = os.path.join(pwd, 'mypaas.toml')
        config = toml.load(path)
        print(f"Reading config from {path}")
    except Exception as e:
        print("No mypaas.toml found. Proceeding with defaults.")
    finally:
        return config
