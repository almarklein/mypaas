import asgineer
import time


time.sleep(2.5)  # emulate a startup time (load assets etc.)

paths = set()


@asgineer.to_asgi
async def main_handler(request):
    # Returns the paths that have been requested so far.
    paths.add(request.path)
    return str(paths)


if __name__ == "__main__":
    asgineer.run(main_handler, "uvicorn", "0.0.0.0:80", log_level="warning")
