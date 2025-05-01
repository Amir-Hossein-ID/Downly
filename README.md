# Downly - Python Download Manager

*A fast and efficient Python download manager.*

(For downloading torrents visit [torrentix](https://github.com/Amir-Hossein-ID/torrentix))

## 🚀 Features
- **Synchronous downloads** for faster performance
- **Resume support** for interrupted downloads (even if the process is killed!)
- **Multiple downloads** with a single instance
- **Progress tracking** with a clean CLI output

## 📦 Installation
```sh
pip install downly
```

## 💻 Command Line Usage

```sh
downly https://example.com/file.zip [options]
```

Use `downly --help` to see options.

## 🐍 Direct Usage

```python
import asyncio
from downly import Downly

async def main():
    downly = Downly()
    download = downly.new_download("https://example.com/file.zip")
    await download.start()

if __name__ =='__main__':
    asyncio.run(main())
```

### Non-Blocking Downloads
```python
async def main():
    downly = Downly()
    download = downly.new_download("https://example.com/file.zip")
    await download.start(block=False)

    await asyncio.sleep(3) # do other stuff while downloading

    await downly.await_downloads() # wait for download to finish
```

### Pause and resume Downloads
```python
async def main():
    downly = Downly()
    download = downly.new_download("https://example.com/file.zip")
    await download.start(block=False)

    await download.pause()

    # do other stuff

    await download.start() # resume download
```

### Multiple Downloads
```python
async def main():
    downly = Downly()
    downly.new_download("https://example.com/file.zip")
    downly.new_download("https://example.com/file2.zip")
    downly.new_download("https://example.com/file3.zip")
    await downly.await_downloads()
```

### Automatically Saves download state
- Start download: `await download.start()`
- Something Happens and the process terminates:
```sh
file.zip  29% ━━━━━━━━━━━╸━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 4.4/15.1 MB 0:00:03 0:00:07 1.6 MB/s
Ctrl^C (Keyboard Interrupt)
```
- Start Download Again: `await d.start()`
- Download starts from where it was stopped:
```sh
file.zip  29% ━━━━━━━━━━━╸━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 4.4/15.1 MB 0:00:03 0:00:07 1.6 MB/s
```

## 🛠 Configuration
You can customize download's settings by passing options:
```python
async def main():
    downly = Downly()
    download = downly.new_download(
        "https://example.com/file.zip",
        path='myfolder/myfilename.zip',
        chunk_size=1024*1024*2, # 2MB
        n_connections=16 # 16 synchronous connections 
    )
    await download.start()
```


## 🔥 Roadmap
- [ ] Proxies Support
- [ ] More control over User agents, number of retries, ...

## 📜 License
MIT License. See [LICENSE](LICENSE) for details.
