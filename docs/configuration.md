# Configuration


## Using mypaas.toml

Since the maximum file size to push is restricted to 100MB, it is important that some files are not pushed to the server.
This would take a long time and anyways, you shouldn't have large binary files in your code.

Mypaas ignores the following files by default `__pycache__`, `htmlcov`, `.git`, `node_modules`.
You can override this behavior by placing the `mypaas.toml` file in the root of your deployment directory.

An example configuration could look like this:

```toml

# Ignore these folders
ignore = ["public", "node_modules", "bin"]

```
