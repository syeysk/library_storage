import requests
import base64

from pykeepass import PyKeePass
from pykeepass.exceptions import CredentialsError

from constants import DEFAULT_PASSWORD_FILEPATH, GITHUB_KNOWLEDGE_OWNER, GITHUB_KNOWLEDGE_REPO


def get_password_data(
    service_name,
    group='main',
    app_name=True,
    password_filepath=DEFAULT_PASSWORD_FILEPATH,
    password='',
):
    try:
        pk = PyKeePass(password_filepath, password=password)
    except CredentialsError as error:
        print('Invalid password:', error)
        raise Exception from error

    title = f'{service_name}_{group}' if group else service_name
    if app_name:
        title = f'storage_scanner_{title}'
    password_data = pk.find_entries(title=title, first=True)
    return password_data


class BaseService:
    SERVICE_NAME = None

    def __init__(self, title, body, password_filepath='DEFAULT_PASSWORD_FILEPATH', password=''):
        self.title = title
        self.body = body
        self._password_filepath = password_filepath
        self._password = password

    def get_password_data(self, group='main'):
        return get_password_data(
            self.SERVICE_NAME,
            group=group,
            password_filepath=self._password_filepath,
            password=self._password,
        )


class SyeyskService(BaseService):
    SERVICE_NAME = 'syeysk'

    def __init__(self, **kwargs):
        super(SyeyskService, self).__init__(**kwargs)

        self.url = 'https://syeysk.ru/api/blog/{method}/'
        password_data = self.get_password_data()
        self.token = password_data.password
        self.headers = {'HTTP_AUTHORIZATION': f'Token {self.token}'}

        parts = self.body.split('\n', 1)
        self.cut = parts[0] if parts else ''
        self.body = parts[1] if len(parts) > 1 else self.cut

    def create_note(self):
        data = {'title': self.title, 'content': self.body, 'cut': self.cut}
        response = requests.post(self.url.format(method='create_article'), json=data, headers=self.headers)
        if response.status_code == 200:
            response_data = response.json()
            return True, {'id': response_data['id'], 'url': response_data['url']}

        return False, response.text

    def update_note(self, note_id):
        data = {'article_id': note_id, 'title': self.title, 'content': self.body, 'cut': self.cut}
        response = requests.post(self.url.format(method='update_article'), json=data, headers=self.headers)
        if response.status_code == 200:
            response_data = response.json()
            return True, {'url': response_data['url']}

        return False, response.text


class DevelopsocService(BaseService):
    SERVICE_NAME = 'Developsoc'

    def __init__(self, **kwargs):
        super(DevelopsocService, self).__init__(**kwargs)

    def create_note(self):
        print('----', self._password)
        return {'id': 'article_name', 'url': 'https://developsoc.ru/article_name',
                'publicate_datetime': '2022-09-12 23:10'}

    def update_note(self, note_id):
        return {}


class GithubService(BaseService):
    """Имя форка должно соответствовать оригиналу, форк должен быть прямым потомком оригинала"""
    url_template = 'https://api.github.com{}'
    SERVICE_NAME = 'knowledge_github'

    def __init__(self, **kwargs):
        super(GithubService, self).__init__(**kwargs)
        self.knowledge_owner = GITHUB_KNOWLEDGE_OWNER
        self.knowledge_repo = GITHUB_KNOWLEDGE_REPO
        password_data = self.get_password_data()
        self.token = password_data.password
        self.owner = password_data.username
        self.branch = 'notes-from-extern-service'
        self.prefix_filepath = 'db/'
        self.headers = {'Accepts': 'application/vnd.github+json'}
        self.auth = (self.owner, self.token)

    def get_url(self, url_path):
        return self.url_template.format(url_path)

    def has_fork(self):
        url = self.get_url(f'/repos/{self.owner}/{self.knowledge_repo}')
        response = requests.get(url, auth=self.auth, headers=self.headers)
        # print('has_fork()', url, response.text, response.status_code)
        if response.status_code == 200:
            data = response.json()
            if data['fork']:
                parent = data['parent']
                if parent and parent['full_name'] == f'{self.knowledge_owner}/{self.knowledge_repo}':
                    return True

    def make_fork(self):
        url = self.get_url(f'/repos/{self.knowledge_owner}/{self.knowledge_repo}/forks')
        data = {'default_branch_only': True}
        response = requests.post(url, auth=self.auth, headers=self.headers, json=data, timeout=60 * 5)
        print('make_fork()', url, response.text, response.status_code)
        if response.status_code != 202:
            raise Exception('Error to make fork', response.text)

    def has_branch(self):
        url = self.get_url(f'/repos/{self.owner}/{self.knowledge_repo}/git/ref/heads/{self.branch}')
        response = requests.get(url, auth=self.auth, headers=self.headers)
        if response.status_code == 200:
            return True

        print('has_branch()', url, response.text, response.status_code)

    '''
    def get_last_commit_hash(self):
        url = self.get_url(f'/repos/{self.owner}/{self.knowledge_repo}/commits')
        response = requests.get(url, params={'per_page': 1}, headers=self.headers)
        if response.status_code == 200:
            return response.json()[0]['sha']

        raise Exception('Error getting last commit\'s sh1', response.text)
    '''

    def get_head_branch_hash(self):
        url = self.get_url(f'/repos/{self.owner}/{self.knowledge_repo}/git/ref/heads/main')
        response = requests.get(url, auth=self.auth, headers=self.headers)
        print('get_head_branch_hash()', url, response.text, response.status_code)
        if response.status_code == 200:
            return response.json()['object']['sha']

        raise Exception('Error getting head branch\'s sha', response.text)

    def make_branch(self, sha):
        url = self.get_url(f'/repos/{self.owner}/{self.knowledge_repo}/git/refs')
        data = {
            'ref': f'refs/heads/{self.branch}',
            'sha': sha,
        }
        response = requests.post(url, json=data, auth=self.auth, headers=self.headers)
        print('make_branch()', url, response.text, response.status_code, data)
        if response.status_code != 201:
            raise Exception('Error to make branch', response.text, response.status_code)

    def get_last_pull_request_id(self):
        url = self.get_url(f'/repos/{self.owner}/{self.knowledge_repo}/pulls')
        params = {'per_page': 1, 'head': f'{self.owner}:{self.branch}', 'state': 'open'}
        response = requests.get(url, auth=self.auth, params=params, headers=self.headers)
        if response.status_code == 200:
            pull_requests = response.json()
            return pull_requests[0]['id'] if pull_requests else False

        raise Exception('Error getting last Pull Request')

    def make_pull_request(self):
        url = self.get_url(f'/repos/{self.owner}/{self.knowledge_repo}/pulls')
        data = {
            'title': 'The Pull Request from extern app',
            'head': f'{self.owner}:{self.branch}',
            'base': f'main',
            'body': 'This PR was created by external app.'
        }
        response = requests.post(url, auth=self.auth, json=data, headers=self.headers)
        if response.status_code == 201:
            return response.json()['id']

        raise Exception('Error make Pull Request', response.status_code, response.text)

    def send_file(self, file_path: str, file_content: bytes, sha=None):
        url = self.get_url(f'/repos/{self.owner}/{self.knowledge_repo}/contents/{file_path}')
        data = {
            'branch': self.branch,
            'message': '{} file from external app'.format('update' if sha else 'add'),
            'content': str(base64.b64encode(file_content), 'utf-8')
        }
        if sha:
            data['sha'] = sha

        response = requests.put(url, auth=self.auth, json=data, headers=self.headers)
        if (sha and response.status_code == 200) or (not sha and response.status_code == 201):
            return response.json()

        raise Exception('Error create or update file', response.status_code, response.text)

    def create_note(self):
        try:
            created = False
            if not self.has_fork():
                self.make_fork()
                created = True

            if created or not self.has_branch():
                sha = self.get_head_branch_hash()
                self.make_branch(sha)
                created = True

            file_path = f'{self.prefix_filepath}{self.title}.md'
            file_content = bytes(f'#{self.title}\n\n{self.body}\n', 'utf-8')
            file_data = self.send_file(file_path=file_path, file_content=file_content)

            # last_pull_requst_id = self.get_last_pull_request_id()
            # if created or not last_pull_requst_id:
            #     self.make_pull_request()

            #url = f'https://github.com/{self.owner}/{self.knowledge_repo}/blob/{self.branch}/{file_path}'
            return True, {'id': file_data['content']['sha'], 'url': file_data['content']['html_url']}
        except Exception as error:
            error_str = str(error)
            return False, error_str

