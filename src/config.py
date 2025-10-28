import json
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
EXAMPLE_CONFIG_PATH = BASE_DIR / 'config.example.json'


class Config:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)

        return cls._instance

    def __init__(self):
        self.storage_books = None
        self.storage_notes = None
        self.db_path = None
        self.config_path = BASE_DIR / 'config.json'

        if not self.config_path.exists():
            if (hasattr(EXAMPLE_CONFIG_PATH, 'copy')):
                EXAMPLE_CONFIG_PATH.copy(self.config_path) # since Python 3.14
            else:
                from shutil import copyfile
                copyfile(EXAMPLE_CONFIG_PATH, self.config_path)

        self.load()
    
    def load(self):
        with self.config_path.open(encoding='utf-8') as fjson:
            data = json.load(fjson)
            self.storage_books = Path(data['storage_books']).resolve()
            self.storage_notes = Path(data['storage_notes']).resolve()

        self.db_path = self.storage_books / 'sqlite3.db'

    def dump(self):
        with self.config_path.open('w', encoding='utf-8') as fjson:
            data = {'storage_books': self.storage_books, 'storage_notes': self.storage_notes}
            json.dump(fjson, data)

    def set_storage_books(self, value: Path):
        self.storage_books = value
        self.db_path = self.storage_books / 'sqlite3.db'
        self.dump()

    def set_storage_notes(self, value: Path):
        self.storage_notes = value
        self.dump()


config = Config()
