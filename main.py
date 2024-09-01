from time import sleep
from download import download_with_ffmpeg, download_with_ytdlp, get_key_drm, get_license, get_pssh, save_html, save_link, save_question, ytdlp_options
from login import requests, cyclesession, selected_course
from utils import json, clear_folder_name, decode_content, logger, os, create_folder
from tqdm import tqdm
from dl_xanas import download_bunny_video
from time import sleep

from concurrent.futures import ThreadPoolExecutor, as_completed


def data_modules(course_name, course_link):
  folder_course = create_folder(clear_folder_name(course_name))
  url = f"https://portal.fullcycle.com.br/api/cursos/turma/{course_link['class']}/categoria/{course_link['id']}/list.json"
  response = cyclesession.get(url).json()
  modules_data = {}
  for data in response:
    modules_data[data['nome']] = {'id': data['id'], 'path':folder_course, 'class': course_link['class']}
  return modules_data


def get_response(url, max_attempts=3):
  for _ in range(max_attempts):
    response = requests.get(url)
    if response.status_code == 200:
      return response
    sleep(2)
  response.raise_for_status()


def process_lesson_data(path, lesson_data):
  for i, data in enumerate(lesson_data, start=1):
    if data.get('tipo') == 1:
      lesson_title, video_url = f"{i:03d} - {data['titulo']}", data['video_url']
      path_lesson_media = create_folder(os.path.join(path, clear_folder_name(lesson_title)))
      download_path = os.path.join(path_lesson_media, 'aula')
      ydl_opts = ytdlp_options(video_url, download_path)
      download_with_ytdlp(ydl_opts, video_url)
    elif data.get('tipo') == 7:
      lesson_title, lesson_url = f'{i:03d} - {data["titulo"]}', f'{data["url"]}/stream.mpd'
      path_lesson_media = create_folder(os.path.join(path, clear_folder_name(lesson_title)))
      response = get_response(lesson_url)
      pssh = get_pssh(response)
      decryption_key = get_key_drm(get_license(data["custom_data"]), pssh)
      download_path = os.path.join(path_lesson_media, 'aula')
      download_with_ffmpeg(decryption_key, download_path, lesson_url)
      if data.get('transcription'):
        lesson_title = f"{i:03d} - {data['titulo']}"
        path_lesson_transcription = create_folder(os.path.join(path, clear_folder_name(lesson_title)))
        save_html(path_lesson_transcription, data['transcription'], '#FFFFFF', transcricao=True)
    elif data.get('tipo') == 2:
      lesson_title, lesson_text = f'{i:03d} - {data["titulo"]}', data['texto_changed']
      path_lesson_text = create_folder(os.path.join(path, clear_folder_name(lesson_title)))
      save_html(path_lesson_text, lesson_text, '#333')
    elif data.get('tipo') == 8:
      lesson_title, lesson_link = f"{i:03d} - {data['titulo']}", data['link']
      path_lesson_link = create_folder(os.path.join(path, clear_folder_name(lesson_title)))
      save_link(path_lesson_link, lesson_link)
    elif data.get('tipo') == 6:
      lesson_title, lesson_project = f"{i:03d} - {data['titulo']}", data['projeto_fase']['id']
      path_lesson_project = create_folder(os.path.join(path, clear_folder_name(lesson_title)))
      url = f'https://portal.fullcycle.com.br/api/projetos/fase/{lesson_project}.json'
      response = cyclesession.get(url).json()['descricao']
      save_html(path_lesson_project, response)
    elif data.get('tipo') == 4:
      lesson_title, question_id = f"{i:03d} - {data['titulo']}", data['id']
      path_lesson_question = create_folder(os.path.join(path, clear_folder_name(lesson_title)))
      response = cyclesession.get(f'https://portal.fullcycle.com.br/api/cursos/conteudo/{question_id}/avaliacoes.json').json()
      save_question(path_lesson_question, response)
    elif data.get('tipo') == 12:
      lesson_title, lesson_id = f"{i:03d} - {data['titulo']}", data['id']
      path_lesson_media = create_folder(os.path.join(path, clear_folder_name(lesson_title)))
      download_path = os.path.join(path_lesson_media, 'aula')
      if not os.path.exists(f'{download_path}.mp4'):
        sleep(4)
        url = f'https://portal.fullcycle.com.br/api/cursos/conteudo/{lesson_id}.json'
        response = cyclesession.get(url).json()
        lesson_decode = decode_content(response['content'])
        if lesson_decode.get('video_url_bunny'):
          embed_url = lesson_decode["video_url_bunny"].replace('play', 'embed')
          download_bunny_video(embed_url, download_path)
          if data.get('video_transcription_nivo'):
            lesson_title = f"{i:03d} - {data['titulo']}"
            path_lesson_transcription = create_folder(os.path.join(path, clear_folder_name(lesson_title)))
            save_html(path_lesson_transcription, data['video_transcription_nivo'], '#FFFFFF', transcricao=True)


def process_lessons(lessons):
  with ThreadPoolExecutor(max_workers=3) as executor:
    futures = []
    for lesson_path, lesson_data in lessons.items():
      path = create_folder(lesson_path)
      future = executor.submit(process_lesson_data, path, lesson_data)
      futures.append(future)
    for future in as_completed(futures):
      future.result()


def data_lessons(path, lessons):
  for i, lesson in enumerate(lessons, start=1):
    lesson_data = {}
    title, content = lesson['nome'], lesson['conteudos']
    path_lessons = create_folder(os.path.join(path, f'{i:03d} - {clear_folder_name(title)}'))
    lesson_data[path_lessons] = content
    process_lessons(lesson_data)


def process_modules(modules):
  total_modules, success_index = len(modules), 0
  for module_title, module_data in tqdm(modules.items(), total=total_modules, desc='Processing Modules'):
    url = f"https://portal.fullcycle.com.br/api/cursos/turma/{module_data['class']}/curso/{module_data['id']}/capitulos.json?expand_conteudos=1"
    cyclesession.headers['user-agent'] = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36'
    cyclesession.headers['origin'] = 'https://plataforma.fullcycle.com.br'
    cyclesession.headers['referer'] = 'https://plataforma.fullcycle.com.br/'
    response = cyclesession.get(url)
    if response.status_code != 200:
      msg = f"Aviso: {response.json()['message']} ||| {module_title}"
      logger(msg, warning=True)
      continue
    success_index += 1
    module_title = f'{success_index:03d} - {clear_folder_name(module_title)}'
    path_module = create_folder(os.path.join(module_data['path'], module_title))
    decode = decode_content(response.json()['content'])
    data_lessons(path_module, decode)

if __name__ == '__main__':
  course_name, course_link = selected_course
  modules_data = data_modules(course_name, course_link)
  process_modules(modules_data)
