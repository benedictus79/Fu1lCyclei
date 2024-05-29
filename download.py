import subprocess
import os
from bs4 import BeautifulSoup
from login import requests
from utils import logger, shorten_folder_name



def download_with_ffmpeg(decryption_key, name_lesson, url):
  if not os.path.exists(f'{name_lesson}.mp4'):
    cmd = [
      'ffmpeg',
      '-cenc_decryption_key', decryption_key,
      '-headers', 'Referer: https://plataforma.fullcycle.com.br/',
      '-y',
      '-i', url,
      '-codec', 'copy',
      '-threads', '4',
      f'{name_lesson}.mp4'
    ]
    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if result.returncode != 0:
      error_message = f'Erro ao baixar a aula {name_lesson}: {result.stderr.decode()}'
      logger(error_message, error=True)

    return result

def get_pssh(response):
  soup = BeautifulSoup(response.text, 'xml')
  pssh_element = soup.find_all('cenc:pssh')[1]
  if pssh_element:
    pssh = pssh_element.text
    return pssh


def get_license(custom_data):
  url = f'https://widevine-dash.ezdrm.com/widevine-php/widevine-foreignkey.php?pX=AC398C&customdata={custom_data}'
  return url


def save_html(content_folder, html, color=None, transcricao=None):
  if '<body' not in html:
    html = f'<html><head><style>body {{ background-color: {color}; }}</style></head><body>{html}</body></html>'
  elif 'style=' not in html:
    html = html.replace('<body', f'<body style="background-color: {color};"')

  content_path = f"{os.path.join(content_folder, 'aula.html')}"

  if transcricao:
    content_path = f"{os.path.join(content_folder, 'transcricao.html')}"

  with open(content_path, 'w', encoding='utf-8') as file:
    file.write(html)


def save_link(link_folder, link_url):
  file_path = shorten_folder_name(os.path.join(link_folder, f'link.txt'))
  if not os.path.exists(file_path):
    with open(file_path, 'w', encoding='utf-8') as file:
      file.write(str(link_url))

def save_question(path, data):
  html_content = '<html>\n<head>\n<title>Questões e Respostas</title>\n</head>\n<body>\n<h1>Questões e Respostas</h1>\n'

  for question in data:
    titulo = question['titulo']
    html_content += f'<h2>{titulo}</h2>\n<ul>\n'
    for resposta in question['respostas']:
      html_content += f"<li>{resposta['resposta']}</li>\n"
    html_content += '</ul>\n'

  html_content += '</body>\n</html>'
  question_path = f"{os.path.join(path, 'questionario.html')}"
  if not os.path.exists(question_path):
    with open(question_path, 'w', encoding='utf-8') as file:
      file.write(html_content)


def get_key_drm(license_url, pssh):
  api_url = 'https://cdrm-project.com/'
  license_url = license_url
  pssh = pssh
  json_data = {
    'PSSH': pssh,
    'License URL': license_url,
    'Headers': '{\n"Accept": "*/*",\n"Accept-Language": "pt-BR,pt;q=0.7",\n"Cache-Control": "no-cache",\n"Content-Type": "application/octet-stream",\n"DNT": "1",\n"Key-System": "com.widevine.alpha",\n"Origin": "https://plataforma.fullcycle.com.br/",\n"Pragma": "no-cache",\n"Referer": "https://plataforma.fullcycle.com.br/",\n"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36"\n}',
    'JSON': '',
    'Cookies': '',
    'Data': '',
    'Proxy': '',
  }
  headers = {
    'Accept-Language': 'pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7,gl;q=0.6,es;q=0.5',
    'Cache-Control': 'no-cache',
    'Connection': 'keep-alive',
    'Origin': 'https://cdrm-project.com',
    'Pragma': 'no-cache',
    'Referer': 'https://cdrm-project.com/',
    'Sec-Fetch-Dest': 'empty',
    'Sec-Fetch-Mode': 'cors',
    'Sec-Fetch-Site': 'same-origin',
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36',
  }
  decryption_results = requests.post(api_url, json=json_data, headers=headers)
  decryption_key = decryption_results.json()['Message'].split(':')[1].strip()
  return decryption_key