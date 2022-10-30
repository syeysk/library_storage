from unittest.mock import patch

from pyfakefs.fake_filesystem_unittest import TestCase

from library_storage_scanner.exporters import CSVExporter
from library_storage_scanner.scanner import DBStorage, LibraryStorage
from tests.library_storage_fabric import LibraryStorageFabric

ORIGIN_DIFF_CSV = (
    'Новый,,file01.txt,4256508e9e2099aa72050b5e00d01745153971e915fa190e4a86079a13ab8e73,1\n'
    'Новый,,file02.txt,982dfb44d32c54183e5399ae180a701d70c1434736645eea98c23e6a81b99d1b,2\n'
    'Новый,,file05.txt,ecefb01d5d2f2cce6d2f51257e4d17b480aec572496cb6b2136740704529f35f,3\n'
    'Новый,,directory01/file03.txt,78f690041494259dbb0ca8e890b9464599f5fc1eeaad20de7c4c16b7761c0039,4\n'
    'Новый,,directory01/file04.txt,90acddd186ee9932103da80265a716c2340cbaeeecaaa1da18b78d8e02f97e72,5\n'
    'Новый,,directory02/file06.txt,186bf48b6b0d045b57d29f6961eb7fd10710cfdcd745384ba0c8015e11eb2363,6\n'
    'Новый,,directory02/file07.txt,30273fefb11ee96b052b34051985952ff551b77bde97ba11c79b7b8ab3dc2a16,7\n'
    'Новый,,directory03/file08.txt,5491aedaa8d92e62f28117a5d5a751c31c917ed05ffd974cd433fd5a9834c554,8\n'
)


def mock_get_file_hash(file_path):
    with open(file_path, 'r') as afile:
        return LibraryStorageFabric.generate_hash(afile.read())


class CoreTestCase(TestCase):
    def create_files(self, files_and_content, library_path=''):
        for file_path, content in files_and_content:
            file_path = f'{library_path}{file_path}'
            self.fs.create_file(file_path=file_path, contents=content)

    def setUp(self):
        self.setUpPyfakefs()
        self.fs.create_dir('/struct')
        self.origin_ls = LibraryStorage()
        self.origin_ls.set_db(DBStorage(':memory:'))
        self.copy_ls = LibraryStorage()
        self.copy_ls.set_db(DBStorage(':memory:'))

    def tearDown(self):
        self.origin_ls.__exit__(None, None, None)
        self.copy_ls.__exit__(None, None, None)

    @patch('library_storage_scanner.scanner.get_file_hash', mock_get_file_hash)
    def test_duplicate_in_origin(self):
        origin_fs = (
            ('/file01.txt', 'content01'),
            ('/file02.txt', 'content02'),
            ('/file05.txt', 'content05'),
            ('/directory01/file03.txt', 'content03'),
            ('/directory01/file04.txt', 'content04'),
            ('/directory02/file06.txt', 'content06'),
            ('/directory02/file07.txt', 'content07'),
            ('/directory03/file08.txt', 'content08'),
            ('/directory01111/duplicate.txt', 'content04'),
        )
        library_path = '/origin'
        origin_storage = LibraryStorageFabric(origin_fs)
        origin_storage.generate_db(excludes=['/directory01111/duplicate.txt'])
        self.create_files(origin_fs, library_path)

        with patch('builtins.print') as mock_print:
            self.origin_ls.scan_to_db(library_path=library_path, process_dublicate='original')
            data_origin = self.origin_ls.db.cu.execute('select * from files').fetchall()
            self.assertEqual(origin_storage.db, data_origin)
            self.assertEqual(1, mock_print.call_count)
            self.assertEqual(
                'Обнаружен дубликат по хешу:\n'
                '   В базе: directory01/file04.txt\n'
                '    Дубль: directory01111/duplicate.txt',
                mock_print.mock_calls[0].args[0],
            )

    def test_duplicate_in_copy(self):
        origin_fs = (
            ('/origin/file01.txt', 'content01'),
            ('/origin/file02.txt', 'content02'),
            ('/origin/file05.txt', 'content05'),
            ('/origin/directory01/file03.txt', 'content03'),
            ('/origin/directory01/file04.txt', 'content04'),
            ('/origin/directory02/file06.txt', 'content06'),
            ('/origin/directory02/file07.txt', 'content07'),
            ('/origin/directory03/file08.txt', 'content08'),
        )
        origin_db = [
            ('4256508e9e2099aa72050b5e00d01745153971e915fa190e4a86079a13ab8e73', 1, '', 'file01.txt', 0),
            ('982dfb44d32c54183e5399ae180a701d70c1434736645eea98c23e6a81b99d1b', 2, '', 'file02.txt', 0),
            ('ecefb01d5d2f2cce6d2f51257e4d17b480aec572496cb6b2136740704529f35f', 3, '', 'file05.txt', 0),
            ('78f690041494259dbb0ca8e890b9464599f5fc1eeaad20de7c4c16b7761c0039', 4, 'directory01', 'file03.txt', 0),
            ('90acddd186ee9932103da80265a716c2340cbaeeecaaa1da18b78d8e02f97e72', 5, 'directory01', 'file04.txt', 0),
            ('186bf48b6b0d045b57d29f6961eb7fd10710cfdcd745384ba0c8015e11eb2363', 6, 'directory02', 'file06.txt', 0),
            ('30273fefb11ee96b052b34051985952ff551b77bde97ba11c79b7b8ab3dc2a16', 7, 'directory02', 'file07.txt', 0),
            ('5491aedaa8d92e62f28117a5d5a751c31c917ed05ffd974cd433fd5a9834c554', 8, 'directory03', 'file08.txt', 0),
        ]
        origin_struct_1 = (
            '4256508e9e2099aa72050b5e00d01745153971e915fa190e4a86079a13ab8e73,1,,file01.txt\n'
            '982dfb44d32c54183e5399ae180a701d70c1434736645eea98c23e6a81b99d1b,2,,file02.txt\n'
            'ecefb01d5d2f2cce6d2f51257e4d17b480aec572496cb6b2136740704529f35f,3,,file05.txt\n'
            '78f690041494259dbb0ca8e890b9464599f5fc1eeaad20de7c4c16b7761c0039,4,directory01,file03.txt\n'
            '90acddd186ee9932103da80265a716c2340cbaeeecaaa1da18b78d8e02f97e72,5,directory01,file04.txt\n'
            '186bf48b6b0d045b57d29f6961eb7fd10710cfdcd745384ba0c8015e11eb2363,6,directory02,file06.txt\n'
            '30273fefb11ee96b052b34051985952ff551b77bde97ba11c79b7b8ab3dc2a16,7,directory02,file07.txt\n'
            '5491aedaa8d92e62f28117a5d5a751c31c917ed05ffd974cd433fd5a9834c554,8,directory03,file08.txt\n'
        )
        copy_fs = (
            ('/copy/file01.txt', 'content01'),
            ('/copy/file05.txt', 'content05'),
            ('/copy/directory01/file03.txt', 'content03'),
            ('/copy/directory01/file04.txt', 'content04'),
            ('/copy/directory01/duplicate.txt', 'content05'),
            ('/copy/directory02/file06.txt', 'content06'),
            ('/copy/directory03/file08.txt', 'content08'),
        )
        copy_db = [
            ('4256508e9e2099aa72050b5e00d01745153971e915fa190e4a86079a13ab8e73', 1, '', 'file01.txt', 0),
            ('982dfb44d32c54183e5399ae180a701d70c1434736645eea98c23e6a81b99d1b', 2, '', 'file02.txt', 1),
            ('ecefb01d5d2f2cce6d2f51257e4d17b480aec572496cb6b2136740704529f35f', 3, '', 'file05.txt', 0),
            ('78f690041494259dbb0ca8e890b9464599f5fc1eeaad20de7c4c16b7761c0039', 4, 'directory01', 'file03.txt', 0),
            ('90acddd186ee9932103da80265a716c2340cbaeeecaaa1da18b78d8e02f97e72', 5, 'directory01', 'file04.txt', 0),
            ('186bf48b6b0d045b57d29f6961eb7fd10710cfdcd745384ba0c8015e11eb2363', 6, 'directory02', 'file06.txt', 0),
            ('30273fefb11ee96b052b34051985952ff551b77bde97ba11c79b7b8ab3dc2a16', 7, 'directory02', 'file07.txt', 1),
            ('5491aedaa8d92e62f28117a5d5a751c31c917ed05ffd974cd433fd5a9834c554', 8, 'directory03', 'file08.txt', 0),
        ]
        self.create_files(origin_fs)
        self.create_files(copy_fs)

        self.origin_ls.scan_to_db(library_path='/origin', process_dublicate='original')
        data_origin = self.origin_ls.db.cu.execute('select * from files').fetchall()
        self.assertEqual(origin_db, data_origin)

        self.origin_ls.export_db_to_csv(CSVExporter('/struct', None))
        with open('/struct/1.csv') as struct:
            self.assertEqual(origin_struct_1, struct.read())

        self.copy_ls.import_csv_to_db(csv_path='/struct')
        data_copy = self.copy_ls.db.cu.execute('select * from files').fetchall()
        self.assertEqual(origin_db, data_copy)

        with patch('builtins.print') as mock_print:
            self.copy_ls.scan_to_db(library_path='/copy', process_dublicate='copy')
            data_copy = self.copy_ls.db.cu.execute('select * from files').fetchall()
            self.assertEqual(copy_db, data_copy)
            self.assertEqual(1, mock_print.call_count)
            self.assertEqual(
                f'Обнаружен дубликат по хешу:\n'
                '   В базе: file05.txt\n'
                '    Дубль: directory01/duplicate.txt',
                mock_print.mock_calls[0].args[0],
            )
