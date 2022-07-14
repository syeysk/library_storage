from pyfakefs.fake_filesystem_unittest import TestCase

from library_storage import LibraryStorage


class CoreTestCase(TestCase):

    def create_files(self, files_and_content):
        for file_path, content in files_and_content:
            self.fs.create_file(file_path=file_path, contents=content)

    def setUp(self):
        self.setUpPyfakefs()
        self.lib_storage = LibraryStorage(db_path=':memory:')

    @classmethod
    def setUpClass(cls):
        cls.library_path_changed = 'copy'
        cls.csv_path ='struct.csv'

    def tearDown(self):
        self.lib_storage.__exit__(None, None, None)

    def test_scan_to_db(self):
        files_and_content = (
            ('origin/file01.txt', 'content01'),
            ('origin/file02.txt', 'content02'),
            ('origin/file05.txt', 'content05'),
            ('origin/directory01/file03.txt', 'content03'),
            ('origin/directory01/file04.txt', 'content04'),
            ('origin/directory02/file06.txt', 'content06'),
            ('origin/directory02/file07.txt', 'content07'),
            ('origin/directory03/file08.txt', 'content08'),
        )
        self.create_files(files_and_content)
        self.lib_storage.scan_to_db(library_path='/origin')

    def test_scan_to_db_with_diff(self):
        files_and_content = (
            ('origin/file01.txt', 'content01'),
            ('origin/file02.txt', 'content02'),
            ('origin/file05.txt', 'content05'),
            ('origin/directory01/file03.txt', 'content03'),
            ('origin/directory01/file04.txt', 'content04'),
            ('origin/directory02/file06.txt', 'content06'),
            ('origin/directory02/file07.txt', 'content07'),
            ('origin/directory03/file08.txt', 'content08'),
        )
        self.create_files(files_and_content)
        self.lib_storage.scan_to_db(library_path='/origin', diff_file_path='/diff.zip')
