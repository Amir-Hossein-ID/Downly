import asyncio
from aiohttp import ClientSession
from enum import IntEnum

def human_readable_size(size_in_bytes):
    units = ['B', 'KB', 'MB', 'GB', 'TB', 'PB']
    unit_index = 0
    while size_in_bytes >= 1024 and unit_index < len(units) - 1:
        size_in_bytes /= 1024
        unit_index += 1
    
    return f"{size_in_bytes:.2f} {units[unit_index]}"

user_agent = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:134.0) Gecko/20100101 Firefox/134.0'}

class DownloadStatus(IntEnum):
    init = 0
    ready = 1
    running = 2
    paused = 3
    finished = 4
    error = -1


class Download:
    def __init__(self, url, path, *, chunk_size = 1024*1024*1, n_connections=8):
        self.session: ClientSession = None
        self.url = url
        self.path = path
        self.chunk_size = chunk_size
        self.n_connections = n_connections
        self.status: DownloadStatus = DownloadStatus.init
        self._head_req = None

    async def ensure_session(self):
        if self.session and not self.session.closed():
            return
        self.session = ClientSession(headers=user_agent)
    
    async def _do_head_req(self):
        await self.ensure_session()
        r = await self.session.head(self.url, allow_redirects=True)
        self.url = r.url
        self._head_req = r
        self.status = DownloadStatus.ready
    
    async def get_size(self):
        if not self._head_req:
            await self._do_head_req()
        if 'Content-Length' in self._head_req.headers:
            return int(self._head_req.headers.get('Content-Length'))
        return None
    
    async def download_part(self, semaphore, start, end):
        async with semaphore:
            r = await self.session.get(self.url, headers={'Range': f'bytes={start}-{end}'})
            print(f'downloaded from {human_readable_size(start)} to {human_readable_size(end)} of size {human_readable_size(end - start)}')
            with open(self.path, 'r+b') as f:
                f.seek(start)
                f.write(await r.read())
    
    async def _multi_download(self):
        semaphore = asyncio.Semaphore(self.n_connections)
        tasks = [
            self.download_part(semaphore, where, where + self.chunk_size)
            for where in range(0, await self.get_size(), self.chunk_size)
        ]

        await asyncio.gather(*tasks)
        await self.close()
    
    async def download(self):
        if not self._head_req:
            await self._do_head_req()
        self.status = DownloadStatus.running
        open(self.path, 'w').close()
        file_size = await self.get_size()
        if file_size == None:
            pass #TODO
        if self._head_req.headers.get('Accept-Ranges', 'none') == 'none':
            await self._single_download()
            return
        
        await self._multi_download()

    async def _chunks_of_size(self, stream, size):
        while True:
            try:
                data = await stream.readexactly(size)
            except asyncio.IncompleteReadError as r:
                data = r.partial
                break
            finally:
                yield data

    async def _single_download(self):
        r = await self.session.get(self.url)
        where = 0
        with open(self.path, 'r+b') as f:
            async for data in self._chunks_of_size(r.content, self.chunk_size):
                f.seek(where)
                f.write(data)
                where += len(data)
                print(f'downloaded {human_readable_size(where)}')
        await self.close()

    async def close(self):
        await self.session.close()

async def main():
    url = 'https://dl3.soft98.ir/win/Office.2013-2024.C2R.Install.v7.7.7.7.24.rar?1739645733'
    d = Download(url, 's.rar')
    await d.download()

if __name__ == '__main__':
    asyncio.run(main())
