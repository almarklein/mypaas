import os

import asgineer


# KEY = open('access.key', 'rt').read().strip().replace('\n', '').replace('\r', '')


# os.environ.setdefault("C_ALL", "UTF-8")


@asgineer.to_asgi
async def handle_submit(request):
    """ http handler to post apps.
    """
    print("incoming!", request.path)
    return 200, {}, f"Hi there!"


if __name__ == "__main__":
    asgineer.run(handle_submit, "uvicorn", "0.0.0.0:80", log_level="warning")
