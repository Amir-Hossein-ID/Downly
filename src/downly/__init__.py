from .downly import Downly

__version__ = "0.3.1"

__all__ = [
    "Downly",
]

async def main_download(args):
    downly = Downly()

    for url in args.url:
        downly.new_download(
            url,
            chunk_size=args.chunk_size,
            n_connections=args.number_of_connections
        )

    await downly.await_downloads()

def main():
    import argparse
    import asyncio

    parser = argparse.ArgumentParser(prog="Downly", description="Downly: Yet another download manager in python.")

    parser.add_argument("url", nargs="+", help="URL(s) to download")
    parser.add_argument("-c", "--chunk_size", type=int, help="Chunk size of each download", default=1024*1024*1, required=False)
    parser.add_argument("-n", "--number_of_connections", help="Number of connections for each download", type=int, default=8, required=False)
    parser.add_argument("--version", action="version", version=f"Downly {__version__}")
    # parser.add_argument("-p", "--parallel", type=int, default=4, help="Number of parallel downloads")
    # parser.add_argument("-t", "--timeout", type=int, default=30, help="Timeout for each download in seconds")
    # parser.add_argument("-v", "--verbose", action="store_true", help="Enable verbose output")

    args = parser.parse_args()

    asyncio.run(main_download(args))


if __name__ == "__main__":
    main()
