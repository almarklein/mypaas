"""
Entrypoint for the MyPaas daemon.
"""

import asgineer

from mypaas.daemon import main_handler, SystemStatsProducer


@asgineer.to_asgi
async def main(request):
    return await main_handler(request)


stats_producer = SystemStatsProducer()
stats_producer.start()


if __name__ == "__main__":
    # Host on localhost. Traefik will accept https connections and route via
    # localhost:88. Don't allow direct acces, or we have insecure connection.
    asgineer.run(main, "uvicorn", "localhost:88", log_level="warning")
