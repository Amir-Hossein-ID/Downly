import aiohttp
import aiofiles
import aiofiles.os as aios
from tqdm.asyncio import tqdm

import asyncio
import enum
import os.path
import pickle
from urllib.parse import urlparse, unquote


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
    canceled = 5
    error = -1


class Downloader:
    def __init__(self, url, path=None, *, chunk_size = 1024*1024*1, n_connections=8):
        self.session: aiohttp.ClientSession = None
        self.url = url
        self.path = path
        self.downly_path = path + '.downly' if path else None
        self.dl_path = path + '.downly_partial' if path else None
        self.chunk_size = chunk_size
        self.n_connections = n_connections
        self.status = DownloadStatus.init
        self._head_req = None
        self._semaphore = asyncio.Semaphore(self.n_connections)
        self._progress_bar = None
    
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
    
    async def _download_part(self, part):
        async with self._semaphore:
            if self.status == DownloadStatus.canceled or self.status == DownloadStatus.paused:
                return -1
            r = await self.session.get(self.url, headers={'Range': f'bytes={part[0]}-{part[1]}'})
            async with aiofiles.open(self.dl_path, 'r+b') as f:
                await f.seek(part[0])
                try:
                    async for data, _ in r.content.iter_chunks():
                        await f.write(data)
                        if self._progress_bar is not None:
                            self._progress_bar.update(len(data))
                            self._progress_bar.refresh()
                        if self.status == DownloadStatus.canceled:
                            r.close()
                            return -1
                        if self.status == DownloadStatus.paused:
                            await self._update_parts((part[0], await f.tell()))
                            r.close()
                            return -1
                except asyncio.CancelledError as e:
                    # update the downloaded parts to avoid redownloading later
                    await self._update_parts((part[0], await f.tell()))
                    return -1
                await self._update_parts(part)
    
    async def _update_parts(self, downloaded_part):
        try:
            self._parts.remove(downloaded_part)
        except ValueError:
            for i in range(len(self._parts)):
                if self._parts[i][0] == downloaded_part[0]:
                    self._parts[i] = (downloaded_part[1], self._parts[i][1])
                    break
        
        try:
            async with aiofiles.open(self.downly_path, 'wb') as f:
                await f.write(pickle.dumps(self._parts))
        except asyncio.CancelledError:
            # workaround for task cancellation (e.g Keyboard Interrupt) to avoid ending up with an empty file
            # the above approach gets cancelled again and again before writing the file, so I used a sync version
            with open(self.downly_path, 'wb') as f:
                f.write(pickle.dumps(self._parts))
    
    async def _remaining_parts(self):
        size = await self.get_size()
        if await aios.path.isfile(self.downly_path):
            async with aiofiles.open(self.downly_path, 'rb') as f:
                data = pickle.loads(await f.read())
                return data

        data = [(where, where + self.chunk_size) for where in range(0, await self.get_size(), self.chunk_size)]
        data[-1] = (data[-1][0], size)

        async with aiofiles.open(self.downly_path, 'wb') as f:
            await f.write(pickle.dumps(data))
        return data
    
    async def _multi_download(self):
        async with aiohttp.ClientSession(headers=user_agent) as self.session:
            self._parts = await self._remaining_parts()
            if self._progress_bar is not None:
                new_value = await self.get_size() - sum(i[1]-i[0] for i in self._parts)
                self._progress_bar.n = new_value
                self._progress_bar.last_print_n = new_value
                self._progress_bar.refresh()

            tasks = [
                self._download_part(part)
                for part in self._parts
            ]

            try:
                await asyncio.gather(*tasks)
            except KeyboardInterrupt as e:
                for i in tasks:
                    i.cancel()
        
        if self.status == DownloadStatus.running:
            self.status = DownloadStatus.finished
            await self._clean_up()
        elif self.status == DownloadStatus.canceled:
            await self._clean_up()
    
    async def _single_download(self):
        async with aiohttp.ClientSession(headers=user_agent) as self.session:
            r = await self.session.get(self.url)
            async with aiofiles.open(self.dl_path, 'r+b') as f:
                async for data, _ in r.content.iter_chunks():
                    if self.status == DownloadStatus.canceled:
                        return False
                    await f.write(data)
                    if self._progress_bar is not None:
                        self._progress_bar.update(len(data))
                        self._progress_bar.refresh()
        if self.status == DownloadStatus.running:
            self.status = DownloadStatus.finished
            await self._clean_up()
        elif self.status == DownloadStatus.canceled:
            await self._clean_up()
    
    async def start(self, block=True, progress_bar=True):
        if self.status == DownloadStatus.finished or self.status == DownloadStatus.running \
            or self.status == DownloadStatus.canceled:
            return

        if not self.path:
            self.path = os.path.basename(urlparse(unquote(str(self.url))).path)
            if not self.path:
                raise ValueError("Couldn't get filename from url")
            self.dl_path = self.path + '.downly_partial'
            self.downly_path = self.path + '.downly'

        if not self._head_req:
            await self._do_head_req()
        
        if not (await aios.path.isfile(self.dl_path)):
            open(self.dl_path, 'wb').close()
        file_size = await self.get_size()

        if progress_bar:
            self._progress_bar = tqdm(total=file_size, ncols=70, unit="B", unit_scale=True) if self._progress_bar is None else self._progress_bar
        else:
            self._progress_bar = None

        self.status = DownloadStatus.running

        if await self.is_pausable():
            task = asyncio.create_task(self._multi_download())
        else:
            task = asyncio.create_task(self._single_download())
        
        if not block:
            return task
        else:
            await task
    
    async def pause(self):
        if not (await self.is_pausable()):
            return False
        match self.status:
            case DownloadStatus.init | DownloadStatus.ready:
                # not yet started
                return True
            case DownloadStatus.paused:
                # already paused
                return True
            case DownloadStatus.error:
                # encountered error while downloading -> no pause
                return False
            case DownloadStatus.finished | DownloadStatus.canceled:
                # already finished
                return False
            case DownloadStatus.running:
                self.status = DownloadStatus.paused
            case _:
                # shouldn't reach here
                return False
    
    async def cancel(self):
        match self.status:
            case DownloadStatus.init | DownloadStatus.ready | DownloadStatus.paused \
                | DownloadStatus.canceled | DownloadStatus.running:
                self.status = DownloadStatus.canceled
                return True
            case DownloadStatus.error:
                return False
            case DownloadStatus.finished:
                return False
            case _:
                # shouldn't reach here
                return False
    
    async def _clean_up(self):
        if self.status == DownloadStatus.finished:
            await aios.replace(self.dl_path, self.path)
        else:
            if await aios.path.isfile(self.dl_path):
                await aios.remove(self.dl_path)
        if await aios.path.isfile(self.downly_path):
            await aios.remove(self.downly_path)
