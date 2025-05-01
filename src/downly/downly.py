from rich.progress import Progress, TextColumn, BarColumn, \
    TimeElapsedColumn, TimeRemainingColumn, SpinnerColumn, \
    DownloadColumn, TransferSpeedColumn, TaskProgressColumn

from .download import Downloader, DownloadStatus

instance = None

class Downly():
    def __init__(self):
        global instance
        if instance is not None:
            return instance
        self._progress = Progress(
            TextColumn("[progress.description]{task.description}"),
            TaskProgressColumn(),
            BarColumn(),
            DownloadColumn(),
            TimeElapsedColumn(),
            TimeRemainingColumn(),
            TransferSpeedColumn()
        )
        self.downloads = []
        instance = self
    
    def new_download(self, url, path=None, chunk_size=1024*1024*1, n_connections=8):
        downloader = Downloader(url, path, chunk_size, n_connections, self._progress)
        self.downloads.append(downloader)
        return downloader
    
    async def await_downloads(self):
        for downloader in self.downloads:
            await downloader.start(block=False)
        for downloader in self.downloads:
            if downloader.task != None:
                await downloader.task
