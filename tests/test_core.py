import zipfile

from pyfakefs.fake_filesystem_unittest import TestCase

from library_storage import LibraryStorage

ORIGIN_FS = (
    ('/origin/file01.txt', 'content01'),
    ('/origin/file02.txt', 'content02'),
    ('/origin/file05.txt', 'content05'),
    ('/origin/directory01/file03.txt', 'content03'),
    ('/origin/directory01/file04.txt', 'content04'),
    ('/origin/directory02/file06.txt', 'content06'),
    ('/origin/directory02/file07.txt', 'content07'),
    ('/origin/directory03/file08.txt', 'content08'),
)
ORIGIN_DB = [
    ('4256508e9e2099aa72050b5e00d01745153971e915fa190e4a86079a13ab8e73', 1, '', 'file01.txt', 0),
    ('982dfb44d32c54183e5399ae180a701d70c1434736645eea98c23e6a81b99d1b', 2, '', 'file02.txt', 0),
    ('ecefb01d5d2f2cce6d2f51257e4d17b480aec572496cb6b2136740704529f35f', 3, '', 'file05.txt', 0),
    ('78f690041494259dbb0ca8e890b9464599f5fc1eeaad20de7c4c16b7761c0039', 4, 'directory01', 'file03.txt', 0),
    ('90acddd186ee9932103da80265a716c2340cbaeeecaaa1da18b78d8e02f97e72', 5, 'directory01', 'file04.txt', 0),
    ('186bf48b6b0d045b57d29f6961eb7fd10710cfdcd745384ba0c8015e11eb2363', 6, 'directory02', 'file06.txt', 0),
    ('30273fefb11ee96b052b34051985952ff551b77bde97ba11c79b7b8ab3dc2a16', 7, 'directory02', 'file07.txt', 0),
    ('5491aedaa8d92e62f28117a5d5a751c31c917ed05ffd974cd433fd5a9834c554', 8, 'directory03', 'file08.txt', 0)
]
ORIGIN_DIFF_CSV = (
    'Новый,,file01.txt\r\n'
    'Новый,,file02.txt\r\n'
    'Новый,,file05.txt\r\n'
    'Новый,,directory01/file03.txt\r\n'
    'Новый,,directory01/file04.txt\r\n'
    'Новый,,directory02/file06.txt\r\n'
    'Новый,,directory02/file07.txt\r\n'
    'Новый,,directory03/file08.txt\r\n'
)


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
        self.create_files(ORIGIN_FS)
        self.lib_storage.scan_to_db(library_path='/origin')
        data_origin = self.lib_storage.db.cu.execute('select * from files').fetchall()
        self.assertEqual(ORIGIN_DB, data_origin)

    def test_scan_to_db_with_diff(self):
        self.create_files(ORIGIN_FS)
        self.lib_storage.scan_to_db(library_path='/origin')
        data_origin = self.lib_storage.db.cu.execute('select * from files').fetchall()
        self.assertEqual(ORIGIN_DB, data_origin)
        self.lib_storage.save_diff(library_path='/origin', diff_file_path='/diff.zip')
        with zipfile.ZipFile('/diff.zip', 'r') as diff_zip:
            diff_zip.testzip()
            with diff_zip.open(self.lib_storage.ARCHIVE_DIFF_FILE_NAME, 'r') as diff_file:
                self.assertEqual(ORIGIN_DIFF_CSV, str(diff_file.read(), 'utf-8'))
