import aiohttp
import aiofiles
import aiofiles.os as aios
from tqdm.asyncio import tqdm

import asyncio
import enum
import pickle


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
        self.status = DownloadStatus.init
        self._head_req = None
        self._semaphore = None
    
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
    
    async def is_pausable(self):
        if not self._head_req:
            await self._do_head_req()
        return (await self.get_size()) != None and\
              self._head_req.headers.get('Accept-Ranges', 'none') != 'none'
    
    async def _download_part(self, part, progress_bar):
        async with self._semaphore:
            r = await self.session.get(self.url, headers={'Range': f'bytes={part[0]}-{part[1]}'})
            async with aiofiles.open(self.path, 'r+b') as f:
                await f.seek(part[0])
                async for data, _ in r.content.iter_chunks():
                    await f.write(data)
                    if progress_bar is not None: progress_bar.update(len(data))
                await self._update_parts(part)
    
    async def _update_parts(self, downloaded_part):
        self._parts.remove(downloaded_part)
        if self._parts:
            async with aiofiles.open(self.path + '.pydl', 'wb') as f:
                await f.write(pickle.dumps(self._parts))
        else:
            await aios.remove(self.path + '.pydl')
    
    async def _remaining_parts(self):
        size = await self.get_size()
        if await aios.path.isfile(self.path + '.pydl'):
            async with aiofiles.open(self.path + '.pydl', 'rb') as f:
                data = pickle.loads(await f.read())
                return data, size

        data = [(where, where + self.chunk_size) for where in range(0, await self.get_size(), self.chunk_size)]
        data[-1] = (data[-1][0], size)

        async with aiofiles.open(self.path + '.pydl', 'wb') as f:
            await f.write(pickle.dumps(data))
        return data, size
    
    async def _multi_download(self, progress_bar=None):
        async with aiohttp.ClientSession(headers=user_agent) as self.session:
            self._semaphore = asyncio.Semaphore(self.n_connections)
            self._parts, size = await self._remaining_parts()
            if progress_bar is not None:
                a = size - sum(i[1]-i[0] for i in self._parts)
                progress_bar.update(size - sum(i[1]-i[0] for i in self._parts))

            tasks = [
                self._download_part(part, progress_bar)
                for part in self._parts
            ]

            await asyncio.gather(*tasks)
            self.status = DownloadStatus.finished
    
    async def _single_download(self, progress_bar=None):
        async with aiohttp.ClientSession(headers=user_agent) as self.session:
            r = await self.session.get(self.url)
            async with aiofiles.open(self.path, 'r+b') as f:
                async for data, _ in r.content.iter_chunks():
                    await f.write(data)
                    if progress_bar is not None: progress_bar.update(len(data))
            self.status = DownloadStatus.finished
    
    async def download(self, block=True, progress_bar=True):
        if not block:
            return asyncio.create_task(self.download(progress_bar))

        if not self._head_req:
            await self._do_head_req()
        self.status = DownloadStatus.running
        open(self.path, 'w').close()
        file_size = await self.get_size()

        progress_bar = tqdm(total=file_size, ncols=70, unit="B", unit_scale=True) if progress_bar else None

        if await self.is_pausable():
            await self._multi_download(progress_bar)
        else:
            await self._single_download(progress_bar)


async def main():
    url = 'https://dl3.soft98.ir/win/AAct.4.3.1.rar?1739730472'
    # url = 'https://github.com/Amir-Hossein-ID/Advent-of-Code/archive/refs/heads/master.zip'
    # url = 'https://repo.anaconda.com/archive/Anaconda3-2022.10-Linux-s390x.sh'
    d = Download(url, 's.rar', n_connections=2)
    download = await d.download(block=False)
    await download

if __name__ == '__main__':
    asyncio.run(main())
