import datetime
import asgineer


@asgineer.to_asgi
async def main_handler(request):
    return 200, {}, f"Hello world! Server time: " + str(datetime.datetime.now())


if __name__ == "__main__":
    asgineer.run(main_handler, "uvicorn", "0.0.0.0:80", log_level="warning")
