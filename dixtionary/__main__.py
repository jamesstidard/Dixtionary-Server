import asyncio

from dixtionary.config import Config
from dixtionary.server import create_app


def main():
    app = asyncio.run(create_app(Config))
    app.run(
        host="0.0.0.0",
        port=Config.PORT,
        debug=Config.DEBUG,
        workers=Config.WORKERS,
        auto_reload=False,  # This feature breaks debugger hooks
    )


if __name__ == "__main__":
    main()
