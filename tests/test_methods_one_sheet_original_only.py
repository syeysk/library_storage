import os.path
import copy

from pyfakefs.fake_filesystem_unittest import TestCase

from library_storage_scanner.exporters import CSVExporter
from library_storage_scanner.scanner import DBStorage, LibraryStorage

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
    ('5491aedaa8d92e62f28117a5d5a751c31c917ed05ffd974cd433fd5a9834c554', 8, 'directory03', 'file08.txt', 0),
]
ORIGIN_STRUCT = (
    '4256508e9e2099aa72050b5e00d01745153971e915fa190e4a86079a13ab8e73,1,,file01.txt\n'
    '982dfb44d32c54183e5399ae180a701d70c1434736645eea98c23e6a81b99d1b,2,,file02.txt\n'
    'ecefb01d5d2f2cce6d2f51257e4d17b480aec572496cb6b2136740704529f35f,3,,file05.txt\n'
    '78f690041494259dbb0ca8e890b9464599f5fc1eeaad20de7c4c16b7761c0039,4,directory01,file03.txt\n'
    '90acddd186ee9932103da80265a716c2340cbaeeecaaa1da18b78d8e02f97e72,5,directory01,file04.txt\n'
    '186bf48b6b0d045b57d29f6961eb7fd10710cfdcd745384ba0c8015e11eb2363,6,directory02,file06.txt\n'
    '30273fefb11ee96b052b34051985952ff551b77bde97ba11c79b7b8ab3dc2a16,7,directory02,file07.txt\n'
    '5491aedaa8d92e62f28117a5d5a751c31c917ed05ffd974cd433fd5a9834c554,8,directory03,file08.txt\n'
)


class CoreTestCase(TestCase):
    def create_files(self, files_and_content):
        for file_path, content in files_and_content:
            self.fs.create_file(file_path=file_path, contents=content)

    def setUp(self):
        self.setUpPyfakefs()
        self.create_files(ORIGIN_FS)
        self.fs.create_dir('/struct')
        self.origin_ls = LibraryStorage()
        self.origin_ls.set_db(DBStorage(':memory:'))
        self.origin_ls.scan_to_db(library_path='/origin', process_dublicate='original')

    def tearDown(self):
        self.origin_ls.__exit__(None, None, None)

    def check_second_scanning(self, origin_db_after_second_scanning, origin_struct_after_second_scanning):
        """Общий для тестов метод. Выполяет для оригинальной базы: сканирование хранилища, экспорт"""
        self.origin_ls.scan_to_db(library_path='/origin', process_dublicate='original')
        data_origin = self.origin_ls.db.cu.execute('select * from files').fetchall()
        self.assertEqual(origin_db_after_second_scanning, data_origin)

        self.origin_ls.export_db_to_csv(CSVExporter('/struct', None))
        with open('/struct/1.csv') as struct:
            self.assertEqual(origin_struct_after_second_scanning, struct.read())

    def test_first_scanning(self):
        data_origin = self.origin_ls.db.cu.execute('select * from files').fetchall()
        self.assertEqual(ORIGIN_DB, data_origin)

        self.origin_ls.export_db_to_csv(CSVExporter('/struct', None))
        with open('/struct/1.csv') as struct:
            self.assertEqual(ORIGIN_STRUCT, struct.read())

    def test_without_changing(self):
        self.check_second_scanning(ORIGIN_DB, ORIGIN_STRUCT)

    def test_all_process_delete_file(self):
        deleted_filepath = ORIGIN_FS[3][0]
        self.fs.remove(deleted_filepath)
        origin_db_after_second_scanning = copy.deepcopy(ORIGIN_DB)
        origin_db_after_second_scanning[3] = (
            origin_db_after_second_scanning[3][0],
            origin_db_after_second_scanning[3][1],
            origin_db_after_second_scanning[3][2],
            origin_db_after_second_scanning[3][3],
            1,
        )
        origin_struct_after_second_scanning = ORIGIN_STRUCT.split('\n')
        del origin_struct_after_second_scanning[3]
        self.check_second_scanning(origin_db_after_second_scanning, '\n'.join(origin_struct_after_second_scanning))

    def test_all_process_add_file(self):
        self.fs.create_file(file_path='/origin/directory04/file09.txt', contents='content09')
        origin_db_after_second_scanning = copy.deepcopy(ORIGIN_DB)
        origin_db_after_second_scanning.append(
            ('04d7c338c6683652df6bca24f6ea882833912f800a9c6d9229006e05344fe5df', 9, 'directory04', 'file09.txt', 0),
        )
        origin_struct_after_second_scanning = '{}{}'.format(
            ORIGIN_STRUCT,
            '04d7c338c6683652df6bca24f6ea882833912f800a9c6d9229006e05344fe5df,9,directory04,file09.txt\n',
        )
        self.check_second_scanning(origin_db_after_second_scanning, origin_struct_after_second_scanning)

    def test_all_process_rename_file(self):
        renamed_filepath = ORIGIN_FS[3][0]
        self.fs.rename(renamed_filepath, '{}_renamed'.format(renamed_filepath))
        origin_db_after_second_scanning = copy.deepcopy(ORIGIN_DB)
        origin_db_after_second_scanning[3] = (
            origin_db_after_second_scanning[3][0],
            origin_db_after_second_scanning[3][1],
            origin_db_after_second_scanning[3][2],
            '{}_renamed'.format(origin_db_after_second_scanning[3][3]),
            0,
        )
        origin_struct_after_second_scanning = ORIGIN_STRUCT.split('\n')
        row = origin_struct_after_second_scanning[3].split(',')
        row[-1] = '{}_renamed'.format(row[-1])
        origin_struct_after_second_scanning[3] = ','.join(row)
        self.check_second_scanning(origin_db_after_second_scanning, '\n'.join(origin_struct_after_second_scanning))

    def test_all_process_move_file(self):
        moved_filepath = ORIGIN_FS[3][0]
        new_dirpath = os.path.join(
            os.path.dirname(os.path.dirname(moved_filepath)),
            'new_dir',
        ).replace('\\', '/')
        self.fs.create_dir(new_dirpath)
        new_filepath = os.path.join(
            new_dirpath,
            os.path.basename(moved_filepath),
        )
        self.fs.rename(moved_filepath, new_filepath)
        origin_db_after_second_scanning = copy.deepcopy(ORIGIN_DB)
        origin_db_after_second_scanning[3] = (
            origin_db_after_second_scanning[3][0],
            origin_db_after_second_scanning[3][1],
            new_dirpath.replace('/origin/', ''),
            origin_db_after_second_scanning[3][3],
            0,
        )
        origin_struct_after_second_scanning = ORIGIN_STRUCT.split('\n')
        row = origin_struct_after_second_scanning[3].split(',')
        row[-2] = new_dirpath.replace('/origin/', '')
        origin_struct_after_second_scanning[3] = ','.join(row)
        self.check_second_scanning(origin_db_after_second_scanning, '\n'.join(origin_struct_after_second_scanning))

    """def test_all_process_moved_and_renamed_file(self):
        self.all_process(copy_fs, copy_db, copy_diff_csv, origin_db_after_applying_diff)

    def test_all_process_moved_file_and_add_another_file_with_the_same_name(self):
        self.all_process(copy_fs, copy_db, copy_diff_csv, origin_db_after_applying_diff)
    """
