import aiohttp
import asyncio

user_agent = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:134.0) Gecko/20100101 Firefox/134.0'}

def human_readable_size(size_in_bytes):
    units = ['B', 'KB', 'MB', 'GB', 'TB', 'PB']
    unit_index = 0
    while size_in_bytes >= 1024 and unit_index < len(units) - 1:
        size_in_bytes /= 1024
        unit_index += 1
    
    return f"{size_in_bytes:.2f} {units[unit_index]}"

async def download_part(session: aiohttp.ClientSession, semaphore, url, start, end, path):
    async with semaphore:
        r = await session.get(url, headers={'Range': f'bytes={start}-{end}'})
        print(f'downloaded from {human_readable_size(start)} to {human_readable_size(end)} of size {human_readable_size(end - start)}')
        with open(path, 'r+b') as f:
            f.seek(start)
            f.write(await r.read())

async def download(url, path):
    async with aiohttp.ClientSession(headers=user_agent) as session:
        r = await session.head(url, allow_redirects=True)
        download_url = r.url
        # can_pause = r.headers.get('Accept-Ranges', 'none') != 'none'
        file_size = int(r.headers.get('Content-Length', 0))
        chunk_size = 1024*1024*1
        connections = 3

        with open(path, 'wb') as _:
            pass

        semaphore = asyncio.Semaphore(connections)
        tasks = [
            download_part(session, semaphore, download_url, where, where + chunk_size, path)
            for where in range(0, file_size, chunk_size)
        ]

        await asyncio.gather(*tasks)


if __name__ == '__main__':
    # url = input("Enter URL: ")
    url = 'https://dl3.soft98.ir/win/Office.2013-2024.C2R.Install.v7.7.7.7.24.rar?1739645733'
    asyncio.run(download(url, 'newdownload.rar'))