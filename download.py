import asyncio
import aiohttp
import enum
from tqdm.asyncio import tqdm


def human_readable_size(size_in_bytes):
    units = ['B', 'KB', 'MB', 'GB', 'TB', 'PB']
    unit_index = 0
    while size_in_bytes >= 1024 and unit_index < len(units) - 1:
        size_in_bytes /= 1024
        unit_index += 1
    
    return f"{size_in_bytes:.2f} {units[unit_index]}"

user_agent = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:134.0) Gecko/20100101 Firefox/134.0'}

class DownloadStatus(enum.IntEnum):
    init = 0
    ready = 1
    running = 2
    paused = 3
    finished = 4
    error = -1


class Download:
    def __init__(self, url, path, *, chunk_size = 1024*1024*1, n_connections=8):
        self.session: aiohttp.ClientSession = None
        self.url = url
        self.path = path
        self.chunk_size = chunk_size
        self.n_connections = n_connections
        self.status: DownloadStatus = DownloadStatus.init
        self._head_req = None
    
    def _update(session, context, params):
        pass
    
    async def _do_head_req(self):
        if self.session != None and not self.session.closed:
            r = await self.session.head(self.url, allow_redirects=True)
        else:
            async with aiohttp.ClientSession(headers=user_agent) as session:
                r = await session.head(self.url, allow_redirects=True)
        self.url = r.url
        self._head_req = r
        self.status = DownloadStatus.ready
    
    async def get_size(self):
        if not self._head_req:
            await self._do_head_req()
        if 'Content-Length' in self._head_req.headers:
            return int(self._head_req.headers.get('Content-Length'))
        return None
    
    async def download_part(self, semaphore, start, end, progress_bar):
        async with semaphore:
            r = await self.session.get(self.url, headers={'Range': f'bytes={start}-{end}'})
            with open(self.path, 'r+b') as f:
                f.seek(start)
                async for data, _ in r.content.iter_chunks():
                    f.write(data)
                    if progress_bar is not None: progress_bar.update(len(data))
                return f.tell() - start
    
    async def _multi_download(self, progress_bar=None):
        async with aiohttp.ClientSession(headers=user_agent) as self.session:
            semaphore = asyncio.Semaphore(self.n_connections)
            tasks = [
                self.download_part(semaphore, where, where + self.chunk_size, progress_bar)
                for where in range(0, await self.get_size(), self.chunk_size)
            ]

            await asyncio.gather(*tasks)
            self.status = DownloadStatus.finished
    
    async def _single_download(self, progress_bar=None):
        async with aiohttp.ClientSession(headers=user_agent) as self.session:
            r = await self.session.get(self.url)
            with open(self.path, 'r+b') as f:
                async for data, _ in r.content.iter_chunks():
                    f.write(data)
                    if progress_bar is not None: progress_bar.update(len(data))
            self.status = DownloadStatus.finished
    
    async def download(self):
        if not self._head_req:
            await self._do_head_req()
        self.status = DownloadStatus.running
        open(self.path, 'w').close()
        file_size = await self.get_size()

        progress_bar = tqdm(total=file_size, ncols=70, unit="B", unit_scale=True)
        if file_size == None:
           await self._single_download(progress_bar)
        else:
            self.file_size = file_size
            if self._head_req.headers.get('Accept-Ranges', 'none') == 'none':
                await self._single_download(progress_bar)
            else:
                await self._multi_download(progress_bar)


async def main():
    url = 'https://dl3.soft98.ir/win/AAct.4.3.1.rar?1739730472'
    url = 'https://github.com/Amir-Hossein-ID/Advent-of-Code/archive/refs/heads/master.zip'
    d = Download(url, 's.rar')
    await d.download()

if __name__ == '__main__':
    asyncio.run(main())
