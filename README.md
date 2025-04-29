# Downly - Python Download Manager

*A fast and efficient Python download manager.*

(For downloading torrents visit [torrentix](https://github.com/Amir-Hossein-ID/torrentix))

## 🚀 Features
- **Synchronous downloads** for faster performance
- **Resume support** for interrupted downloads (even if the process is killed!)
- **Progress tracking** with a clean CLI output

## 📦 Installation
```sh
pip install downly
```

## 💻 Command Line Usage

```sh
downly https://example.com/file.zip [options]
```

## 🐍 Direct Usage

```python
import asyncio
from downly import Downloader

async def main():
    d = Downloader("https://example.com/file.zip")
    await d.start()

if __name__ =='__main__':
    asyncio.run(main())
```

### Non-Blocking Downloads
```python
async def main():
    d = Downloader("https://example.com/file.zip")
    download = await d.start(block=False)

    await asyncio.sleep(3) # do other stuff while downloading

    await download # wait for download to finish
```

### Pause and resume Downloads
```python
async def main():
    d = Downloader("https://example.com/file.zip")
    await d.start(block=False)
    await d.pause()

    # do other stuff

    await d.start() # resume download
```

### Automatically Saves download state
- Start download: `await d.start()`
- Something Happens and the process terminates:
```sh
  7%|██                           | 21.2M/296M [00:12<02:36, 1.75MB/s]
Ctrl^C (Keyboard Interrupt)
```
- Start Download Again: `await d.start()`
- Download starts from where it was stopped:
```sh
  7%|██                           | 21.2M/296M [00:12<02:36, 1.75MB/s]
```

## 🛠 Configuration
You can customize Downly’s settings by passing options:
```python
async def main():
    d = Downloader(
        "https://example.com/file.zip",
        path='myfolder/myfilename.zip',
        chunk_size=1024*1024*2, # 2MB
        n_connections=16) # 16 synchronous connections 
    await d.start()
```


## 🔥 Roadmap
- [ ] Proxies Support
- [ ] More control over User agents, number of retries, ...

## 📜 License
MIT License. See [LICENSE](LICENSE) for details.
