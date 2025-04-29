from .download import Downloader, DownloadStatus

__version__ = "0.2.0"

__all__ = [
    "Downloader",
    "DownloadStatus"
]

async def main_download(args):
    downloads = []
    for url in args.url:
        downloader = Downloader(
            url,
            chunk_size=args.chunk_size,
            n_connections=args.number_of_connections
            )
        download = await downloader.start(block=False)
        downloads.append(download)
    for download in downloads:
        await download

def main():
    import argparse
    import asyncio

    parser = argparse.ArgumentParser(prog="Downly", description="Downly: Yet another download manager in python.")

    parser.add_argument("url", nargs="+", help="URL(s) to download")
    parser.add_argument("-c", "--chunk_size", type=int, help="Chunk size of each download", default=1024*1024*1, required=False)
    parser.add_argument("-n", "--number_of_connections", help="Number of connections for each download", type=int, default=8, required=False)
    # parser.add_argument("-p", "--parallel", type=int, default=4, help="Number of parallel downloads")
    # parser.add_argument("-t", "--timeout", type=int, default=30, help="Timeout for each download in seconds")
    # parser.add_argument("-v", "--verbose", action="store_true", help="Enable verbose output")

    args = parser.parse_args()

    asyncio.run(main_download(args))


if __name__ == "__main__":
    main()
