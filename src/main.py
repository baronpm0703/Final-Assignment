import argparse

from src.api.app import create_app

app = create_app()


def main() -> None:
    parser = argparse.ArgumentParser(description="Call Center Analytics Agent")
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", default=8000, type=int)
    args = parser.parse_args()

    import uvicorn

    uvicorn.run("src.main:app", host=args.host, port=args.port, reload=True)


if __name__ == "__main__":
    main()
