import requests
from utils import benedictus_ascii_art, clear_screen


cyclesession = requests.Session()

def credentials():
  benedictus_ascii_art()
  username = input('email: ')
  password = input('senha: ')
  clear_screen()
  return username, password

def login(username, password):
  headers = {
    'accept': 'application/json, text/plain, */*',
    'accept-language': 'pt-BR,pt;q=0.8',
    'authorization': 'Bearer undefined',
    'origin': 'https://plataforma.fullcycle.com.br',
    'priority': 'u=1, i',
    'referer': 'https://plataforma.fullcycle.com.br/',
    'sec-ch-ua': '"Brave";v="125", "Chromium";v="125", "Not.A/Brand";v="24"',
    'sec-ch-ua-mobile': '?0',
    'sec-ch-ua-platform': '"Windows"',
    'sec-fetch-dest': 'empty',
    'sec-fetch-mode': 'cors',
    'sec-fetch-site': 'same-site',
    'sec-gpc': '1',
    'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36',
  }

  files = {
    '_username': (None, username),
    '_password': (None, password),
  }

  response = cyclesession.post('https://portal.fullcycle.com.br/api/login_check', headers=headers, files=files).json()
  return response['token']


def get_courses(token):
  courses = {}
  cyclesession.headers['authorization'] = f'Bearer {token}'
  response = cyclesession.get('https://portal.fullcycle.com.br/api/cursos/my.json').json()
  for course in response:
    if course['ativo'] == True:
      courses[course['categoria']['nome']] = {'class':course['turma']['id'], 'id': course['categoria']['id']}
  return courses


def choose_course(courses):
  print('Cursos disponíveis:')
  for i, course_title in enumerate(courses.keys(), start=1):
    print(f'{i}. {course_title}')
  
  choice = input("Escolha um curso pelo número: ")
  selected_course_title = list(courses.keys())[int(choice) - 1]
  selected_course_link = courses[selected_course_title]
  return selected_course_title, selected_course_link


email, password = credentials()
token = login(email, password)
courses = get_courses(token)
selected_course = choose_course(courses)
