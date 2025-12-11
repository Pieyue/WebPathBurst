#/bin/python3
"""
By Pieyue
github:
"""
import os
import time
import argparse
import asyncio
import async_timeout
import aiohttp
from collections import defaultdict
from datetime import datetime
from colorama import Fore

from fake_header import generate_headers
from process_wrap import load_wrap

WORKPATH = os.path.abspath(__file__)
WORKDIR = os.path.dirname(WORKPATH)

# Set parameters
parser = argparse.ArgumentParser(description="The function of this tool is to burst a Web site path.\nWarning: Don't use for illegal actions!", formatter_class=argparse.RawDescriptionHelpFormatter)

parser.add_argument('-u', '--url', action='store', help='Set the root url.', required=True)
parser.add_argument('-d', '--dict', action='store', required=True, help='Set the path of password dictionary (require).\nor use internal dictionary:PHP,ASP,DIR,JSP,MDB')
parser.add_argument('-c', '--cookie', action='store', help='Use cookie.')
parser.add_argument('-w', '--wrap', action='store', help='Select a wrap you capture as HTTP Header.')
parser.add_argument('-v', '--verbose', action='store_true', help='Switch on the verbose mode.')
parser.add_argument('-o', '--output', action='store', help='Save the result of scan.')
parser.add_argument('-s', '--speed', type=int, action='store', help="Shouldn't set very high.", default=200)
args = parser.parse_args()

# Loading options
ROOT_PATH:str = args.url
if args.dict.upper() in ['PHP', 'ASP', 'DIR', 'JSP', 'MDB']:
    DICT_PATH:str = f'./dict/{args.dict.upper()}.txt'
else:
    DICT_PATH:str = args.dict
VERBOSE:bool = args.verbose
COOKIES:str = args.cookie
OUTPUT:str = args.output
CONCURRENCY = args.speed
TIMEOUT = 5
RETRY = 2
BAN = 0

if OUTPUT:
    f = open(OUTPUT, 'w', encoding='utf-8')
    f.write('URL,Status,Info\n')

COUNTER = defaultdict(int)

async def fetch(session, url):
    global BAN
    """ 扫描单个路径 """
    for _ in range(RETRY):
        if args.wrap:
            HEADER = load_wrap(args.wrap)
        else:
            HEADER = generate_headers(COOKIES) if COOKIES else generate_headers()
        await asyncio.sleep(0.0, 0.5)
        try:
            async with async_timeout.timeout(TIMEOUT):    # 为异步操作设置超时
                async with session.get(url, allow_redirects=False, headers=HEADER) as resp:
                    status = resp.status
                    res = f'{url} --> {status}'
                    if status == 200:
                        print(Fore.GREEN + res)
                        if OUTPUT:
                            f.write(f'{url},{status},OK\n')
                    elif status == 301:
                        print(Fore.BLUE + res)
                        if OUTPUT:
                            f.write(f'{url},{status},Moved Permanently\n')
                    elif status == 302:
                        print(Fore.LIGHTBLUE_EX + res)
                        if OUTPUT:
                            f.write(f'{url},{status},Found\n')
                    elif status == 403:
                        print(Fore.YELLOW + res)
                        if OUTPUT:
                            f.write(f'{url},{status},Forbidden\n')
                    elif status == 401:
                        print(Fore.CYAN + res)
                        if OUTPUT:
                            f.write(f'{url},{status},Unauthorized\n')
                    elif status == 429:
                        BAN += 1
                        print(Fore.RED + '[!] WARNING: You may been banned...')
                        if BAN >= 10:
                            print(Fore.RED + '[!]WARING: Your has been banned!')
                    else:
                        if VERBOSE:
                            print(Fore.RED + f'[-]{url} --> {status}')
                            if OUTPUT:
                                f.write(f'{url},{status},Fail\n')
                    COUNTER[status] += 1
                    return status
        except Exception as e:
            COUNTER['ERROR'] += 1
            if VERBOSE:
                print(Fore.RED + f'[-]Error: {e}')
            continue
    if VERBOSE:
        print(Fore.RED + f'[-] {url} --> Fail')
    return None

async def scan_path(sem, session, path):
    """ 并发控制 """
    global BAN
    if BAN > 10:
        raise aiohttp.ServerDisconnectedError
    url = f"{ROOT_PATH}/{path}"
    async with sem: # 使用sem上下文来限制并发，找过后剩余的任务会在此处等待
        await fetch(session, url)

async def main():
    """ 主函数 """
    sem = asyncio.Semaphore(CONCURRENCY)    # 限制并发数量

    timeout = aiohttp.ClientTimeout(total=None) # 异步操作限时了就不用给http请求限时了
    conn = aiohttp.TCPConnector(ssl=False)  # 创建一个TCP连接器，禁用ssl以允许访问http协议

    async with aiohttp.ClientSession(timeout=timeout, connector=conn) as session:

        tasks = []
        with open(f"{WORKDIR}{DICT_PATH}", 'r', encoding='utf-8', errors='ignore') as f:
            for line in f:
                path = line.strip()
                if not path:
                    continue

                tasks.append(asyncio.create_task(scan_path(sem, session, path)))
                if len(tasks) >= 10000:
                    try:
                        await asyncio.gather(*tasks)
                        tasks.clear()
                    except aiohttp.ServerDisconnectedError:
                        break

        if tasks and BAN < 10:
            try:
                await asyncio.gather(*tasks)
            except aiohttp.ServerDisconnectedError:
                pass

if __name__ == "__main__":
    start = time.time()
    date = datetime.strftime(datetime.now(), '%Y-%m-%d %H:%M:%S')
    print(f'The scan start on {date}...')
    asyncio.run(main())
    census_data = []
    for k, v in COUNTER.items():
        census_data.append(f'{k}:{v}')
    census_data = ', '.join(census_data)
    if OUTPUT:
        f.write(census_data)
        f.close()
    end = time.time()
    print(Fore.RESET + f'Complete! Statistic: {census_data}\n{end-start:.2f} Seconds.')