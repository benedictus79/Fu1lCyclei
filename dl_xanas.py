#!/usr/bin/env python3

import re
import sys
from hashlib import md5
from html import unescape
from random import random
from urllib.parse import urlparse
import requests
import yt_dlp
from utils import SilentLogger


def download_bunny_video(embed_url, download_path):
    user_agent = {
        'sec-ch-ua':
            '"Google Chrome";v="107", "Chromium";v="107", "Not=A?Brand";v="24"',
        'sec-ch-ua-mobile':
            '?0',
        'sec-ch-ua-platform':
            '"Linux"',
        'user-agent':
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/107.0.0.0 Safari/537.36'
    }
    
    session = requests.session()
    session.headers.update(user_agent)
    
    referer = embed_url
    guid = urlparse(embed_url).path.split('/')[-1]
    
    headers = {
        'embed': {
            'authority': 'iframe.mediadelivery.net',
            'accept': '*/*',
            'accept-language': 'en-US,en;q=0.9',
            'cache-control': 'no-cache',
            'pragma': 'no-cache',
            'referer': referer,
            'sec-fetch-dest': 'iframe',
            'sec-fetch-mode': 'navigate',
            'sec-fetch-site': 'cross-site',
            'upgrade-insecure-requests': '1',
        },
        'ping|activate': {
            'accept': '*/*',
            'accept-language': 'en-US,en;q=0.9',
            'cache-control': 'no-cache',
            'origin': 'https://iframe.mediadelivery.net',
            'pragma': 'no-cache',
            'referer': 'https://iframe.mediadelivery.net/',
            'sec-fetch-dest': 'empty',
            'sec-fetch-mode': 'cors',
            'sec-fetch-site': 'same-site',
        },
        'playlist': {
            'authority': 'iframe.mediadelivery.net',
            'accept': '*/*',
            'accept-language': 'en-US,en;q=0.9',
            'cache-control': 'no-cache',
            'pragma': 'no-cache',
            'referer': embed_url,
            'sec-fetch-dest': 'empty',
            'sec-fetch-mode': 'cors',
            'sec-fetch-site': 'same-origin',
        }
    }
    
    embed_response = session.get(embed_url, headers=headers['embed'])
    embed_page = embed_response.text
    
    try:
        server_id = re.search(r'https://video-(.*?)\.mediadelivery\.net', embed_page).group(1)
    except AttributeError:
        sys.exit(1)
    
    headers['ping|activate'].update({'authority': f'video-{server_id}.mediadelivery.net'})
    search = re.search(r'contextId=(.*?)&secret=(.*?)"', embed_page)
    context_id, secret = search.group(1), search.group(2)
    
    file_name_unescaped = re.search(r'og:title" content="(.*?)"', embed_page).group(1)
    file_name_escaped = unescape(file_name_unescaped)
    file_name = re.sub(r'\.[^.]*$.*', '.mp4', file_name_escaped)
    if not file_name.endswith('.mp4'):
        file_name += '.mp4'
    
    def ping(time, paused, res):
        md5_hash = md5(f'{secret}_{context_id}_{time}_{paused}_{res}'.encode('utf8')).hexdigest()
        params = {'hash': md5_hash, 'time': time, 'paused': paused, 'chosen_res': res}
        session.get(f'https://video-{server_id}.mediadelivery.net/.drm/{context_id}/ping', params=params, headers=headers['ping|activate'])
    
    def activate():
        session.get(f'https://video-{server_id}.mediadelivery.net/.drm/{context_id}/activate', headers=headers['ping|activate'])
    
    def main_playlist():
        params = {'contextId': context_id, 'secret': secret}
        response = session.get(f'https://iframe.mediadelivery.net/{guid}/playlist.drm', params=params, headers=headers['playlist'])
        resolutions = re.findall(r'\s*(.*?)\s*/video\.drm', response.text)[::-1]
        if not resolutions:
            sys.exit(2)
        else:
            return resolutions[0]  # highest resolution, -1 for lowest
    
    def video_playlist(resolution):
        params = {'contextId': context_id}
        session.get(f'https://iframe.mediadelivery.net/{guid}/{resolution}/video.drm', params=params, headers=headers['playlist'])
    
    ping(time=0, paused='true', res='0')
    activate()
    resolution = main_playlist()
    video_playlist(resolution)
    
    for i in range(0, 29, 4):  # first 28 seconds, arbitrary (check issue#11)
        ping(time=i + round(random(), 6), paused='false', res=resolution.split('x')[-1])
    
    session.close()
    
    url = [f'https://iframe.mediadelivery.net/{guid}/{resolution}/video.drm?contextId={context_id}']
    ydl_opts = {
        'http_headers': {
            'Referer': embed_url,
            'User-Agent': user_agent['user-agent']
        },
        'logger': SilentLogger(),
        'merge_output_format': 'mp4',
        'concurrent_fragment_downloads': 10,
        'nocheckcertificate': True,
        'outtmpl': f'{download_path}.%(ext)s',
        'restrictfilenames': True,
        'windowsfilenames': True,
        'no_overwrites': True,
        'retries': 50,
        'trim_file_name': 249,
        'fragment_retries': 50,
        'file_access_retries': 50,
        'extractor_retries': 50,
        'quiet': True,
        'continuedl': True,
        'no_progress': True,
        'skip_unavailable_fragments': False,
        'no_warnings': True,
    }
    
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download(url)
