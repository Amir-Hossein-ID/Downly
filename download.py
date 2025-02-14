import requests

user_agent = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:134.0) Gecko/20100101 Firefox/134.0'}

def download(url, path):
    r = requests.head(url, allow_redirects=True, headers=user_agent)
    download_url = r.url
    file_size = float('inf')
    if not r.ok:
        return
    can_pause = r.headers.get('Accept-Ranges', 'none') != 'none'
    file_size = int(r.headers.get('Content-Length', file_size))
    chunk_size = 1024*1024
    with open(path, 'wb') as f:
        f.write(b'\0' * file_size)

    where = 0
    with open(path, 'r+b') as f:
        data = requests.get(download_url, headers={'Range': f'bytes={where}-{where + chunk_size}'})
        while data.ok and data.content:
            f.seek(where)
            f.write(data.content)
            where += int(data.headers.get('Content-Length', chunk_size))
            if data.status_code == 200:
                break
            data = requests.get(download_url, headers={'Range': f'bytes={where}-{where + chunk_size}'})
        if where == file_size:
            print('good')
        else:
            print('bad')    
    

    

if __name__ == '__main__':
    # url = input("Enter URL: ")
    url = 'https://dl3.soft98.ir/win/AAct.4.3.1.rar'
    download(url, 'newdownload.rar')