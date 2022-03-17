"""
Reads the deploy configuration from mypaas.toml file.
"""
import os
import toml

def deploy_config(pwd):
    path = os.path.join(pwd, 'mypaas.toml')
    print(f"Reading config from {path}")
    return toml.load(path)
