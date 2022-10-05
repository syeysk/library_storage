import zipfile

from pyfakefs.fake_filesystem_unittest import TestCase

from library_storage_scanner.scanner import LibraryStorage

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
ORIGIN_STRUCT_1 = (
    '4256508e9e2099aa72050b5e00d01745153971e915fa190e4a86079a13ab8e73,1,,file01.txt\n'
    '982dfb44d32c54183e5399ae180a701d70c1434736645eea98c23e6a81b99d1b,2,,file02.txt\n'
    'ecefb01d5d2f2cce6d2f51257e4d17b480aec572496cb6b2136740704529f35f,3,,file05.txt\n'
    '78f690041494259dbb0ca8e890b9464599f5fc1eeaad20de7c4c16b7761c0039,4,directory01,file03.txt\n'
    '90acddd186ee9932103da80265a716c2340cbaeeecaaa1da18b78d8e02f97e72,5,directory01,file04.txt\n'
    '186bf48b6b0d045b57d29f6961eb7fd10710cfdcd745384ba0c8015e11eb2363,6,directory02,file06.txt\n'
    '30273fefb11ee96b052b34051985952ff551b77bde97ba11c79b7b8ab3dc2a16,7,directory02,file07.txt\n'
    '5491aedaa8d92e62f28117a5d5a751c31c917ed05ffd974cd433fd5a9834c554,8,directory03,file08.txt\n'
)
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


class CoreTestCase(TestCase):
    def create_files(self, files_and_content):
        for file_path, content in files_and_content:
            self.fs.create_file(file_path=file_path, contents=content)

    def setUp(self):
        self.setUpPyfakefs()
        self.create_files(ORIGIN_FS)
        self.fs.create_dir('/struct')
        self.origin_ls = LibraryStorage(db_path=':memory:')
        self.copy_ls = LibraryStorage(db_path=':memory:')

    def tearDown(self):
        self.origin_ls.__exit__(None, None, None)
        self.copy_ls.__exit__(None, None, None)

    def all_process(self, copy_fs, copy_db, copy_diff_csv, origin_db_after_applying_diff):
        self.create_files(copy_fs)

        self.origin_ls.scan_to_db(library_path='/origin', process_dublicate='original')
        data_origin = self.origin_ls.db.cu.execute('select * from files').fetchall()
        self.assertEqual(ORIGIN_DB, data_origin)

        self.origin_ls.export_db_to_csv('/struct')
        with open('/struct/1.csv') as struct:
            self.assertEqual(ORIGIN_STRUCT_1, struct.read())

        self.copy_ls.import_csv_to_db(csv_path='/struct')
        data_copy = self.copy_ls.db.cu.execute('select * from files').fetchall()
        self.assertEqual(ORIGIN_DB, data_copy)

        self.copy_ls.scan_to_db(library_path='/copy', process_dublicate='copy')
        data_copy = self.copy_ls.db.cu.execute('select * from files').fetchall()
        self.assertEqual(copy_db, data_copy)

        self.copy_ls.save_diff(library_path='/copy', diff_file_path='/diff.zip')
        with zipfile.ZipFile('/diff.zip', 'r') as diff_zip:
            diff_zip.testzip()
            with diff_zip.open(self.copy_ls.ARCHIVE_DIFF_FILE_NAME, 'r') as diff_file:
                self.assertEqual(copy_diff_csv, str(diff_file.read(), 'utf-8'))

        self.origin_ls.apply_diff(library_path='/origin', diff_file_zip_path='/diff.zip')
        data_origin = self.origin_ls.db.cu.execute('select * from files').fetchall()
        self.assertEqual(origin_db_after_applying_diff, data_origin)

    def test_scan_to_db_with_diff(self):
        self.origin_ls.scan_to_db(library_path='/origin', process_dublicate='original')
        data_origin = self.origin_ls.db.cu.execute('select * from files').fetchall()
        self.assertEqual(ORIGIN_DB, data_origin)
        self.origin_ls.save_diff(library_path='/origin', diff_file_path='/diff.zip')
        with zipfile.ZipFile('/diff.zip', 'r') as diff_zip:
            diff_zip.testzip()
            with diff_zip.open(self.origin_ls.ARCHIVE_DIFF_FILE_NAME, 'r') as diff_file:
                self.assertEqual(ORIGIN_DIFF_CSV, str(diff_file.read(), 'utf-8'))

    def test_all_process_delete_file(self):
        copy_fs = (
            ('/copy/file01.txt', 'content01'),
            ('/copy/file05.txt', 'content05'),
            ('/copy/directory01/file03.txt', 'content03'),
            ('/copy/directory01/file04.txt', 'content04'),
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
        copy_diff_csv = (
            'Удалён,file02.txt,,982dfb44d32c54183e5399ae180a701d70c1434736645eea98c23e6a81b99d1b,2\n'
            'Удалён,directory02/file07.txt,,30273fefb11ee96b052b34051985952ff551b77bde97ba11c79b7b8ab3dc2a16,7\n'
        )
        origin_db_after_applying_diff = [
            ('4256508e9e2099aa72050b5e00d01745153971e915fa190e4a86079a13ab8e73', 1, '', 'file01.txt', 0),
            ('ecefb01d5d2f2cce6d2f51257e4d17b480aec572496cb6b2136740704529f35f', 3, '', 'file05.txt', 0),
            ('78f690041494259dbb0ca8e890b9464599f5fc1eeaad20de7c4c16b7761c0039', 4, 'directory01', 'file03.txt', 0),
            ('90acddd186ee9932103da80265a716c2340cbaeeecaaa1da18b78d8e02f97e72', 5, 'directory01', 'file04.txt', 0),
            ('186bf48b6b0d045b57d29f6961eb7fd10710cfdcd745384ba0c8015e11eb2363', 6, 'directory02', 'file06.txt', 0),
            ('5491aedaa8d92e62f28117a5d5a751c31c917ed05ffd974cd433fd5a9834c554', 8, 'directory03', 'file08.txt', 0),
        ]
        self.all_process(copy_fs, copy_db, copy_diff_csv, origin_db_after_applying_diff)

    def test_all_process_add_file(self):
        copy_fs = (
            ('/copy/file01.txt', 'content01'),
            ('/copy/file02.txt', 'content02'),
            ('/copy/file05.txt', 'content05'),
            ('/copy/directory01/file03.txt', 'content03'),
            ('/copy/directory01/file04.txt', 'content04'),
            ('/copy/directory02/file06.txt', 'content06'),
            ('/copy/directory02/file07.txt', 'content07'),
            ('/copy/directory03/file08.txt', 'content08'),
            ('/copy/directory04/file09.txt', 'content09'),
        )
        copy_db = [
            ('4256508e9e2099aa72050b5e00d01745153971e915fa190e4a86079a13ab8e73', 1, '', 'file01.txt', 0),
            ('982dfb44d32c54183e5399ae180a701d70c1434736645eea98c23e6a81b99d1b', 2, '', 'file02.txt', 0),
            ('ecefb01d5d2f2cce6d2f51257e4d17b480aec572496cb6b2136740704529f35f', 3, '', 'file05.txt', 0),
            ('78f690041494259dbb0ca8e890b9464599f5fc1eeaad20de7c4c16b7761c0039', 4, 'directory01', 'file03.txt', 0),
            ('90acddd186ee9932103da80265a716c2340cbaeeecaaa1da18b78d8e02f97e72', 5, 'directory01', 'file04.txt', 0),
            ('186bf48b6b0d045b57d29f6961eb7fd10710cfdcd745384ba0c8015e11eb2363', 6, 'directory02', 'file06.txt', 0),
            ('30273fefb11ee96b052b34051985952ff551b77bde97ba11c79b7b8ab3dc2a16', 7, 'directory02', 'file07.txt', 0),
            ('5491aedaa8d92e62f28117a5d5a751c31c917ed05ffd974cd433fd5a9834c554', 8, 'directory03', 'file08.txt', 0),
            ('04d7c338c6683652df6bca24f6ea882833912f800a9c6d9229006e05344fe5df', 9, 'directory04', 'file09.txt', 0),
        ]
        copy_diff_csv = (
            'Новый,,directory04/file09.txt,04d7c338c6683652df6bca24f6ea882833912f800a9c6d9229006e05344fe5df,9\n'
        )
        origin_db_after_applying_diff = [
            ('4256508e9e2099aa72050b5e00d01745153971e915fa190e4a86079a13ab8e73', 1, '', 'file01.txt', 0),
            ('982dfb44d32c54183e5399ae180a701d70c1434736645eea98c23e6a81b99d1b', 2, '', 'file02.txt', 0),
            ('ecefb01d5d2f2cce6d2f51257e4d17b480aec572496cb6b2136740704529f35f', 3, '', 'file05.txt', 0),
            ('78f690041494259dbb0ca8e890b9464599f5fc1eeaad20de7c4c16b7761c0039', 4, 'directory01', 'file03.txt', 0),
            ('90acddd186ee9932103da80265a716c2340cbaeeecaaa1da18b78d8e02f97e72', 5, 'directory01', 'file04.txt', 0),
            ('186bf48b6b0d045b57d29f6961eb7fd10710cfdcd745384ba0c8015e11eb2363', 6, 'directory02', 'file06.txt', 0),
            ('30273fefb11ee96b052b34051985952ff551b77bde97ba11c79b7b8ab3dc2a16', 7, 'directory02', 'file07.txt', 0),
            ('5491aedaa8d92e62f28117a5d5a751c31c917ed05ffd974cd433fd5a9834c554', 8, 'directory03', 'file08.txt', 0),
            ('04d7c338c6683652df6bca24f6ea882833912f800a9c6d9229006e05344fe5df', 9, 'directory04', 'file09.txt', 0),
        ]
        self.all_process(copy_fs, copy_db, copy_diff_csv, origin_db_after_applying_diff)

    def test_all_process_rename_file(self):
        copy_fs = (
            ('/copy/file01.txt', 'content01'),
            ('/copy/file02.txt', 'content02'),
            ('/copy/file05.txt', 'content05'),
            ('/copy/directory01/file03.txt', 'content03'),
            ('/copy/directory01/file04.txt', 'content04'),
            ('/copy/directory02/file06_renamed.txt', 'content06'),
            ('/copy/directory02/file07.txt', 'content07'),
            ('/copy/directory03/file08.txt', 'content08'),
        )
        copy_db = [
            ('4256508e9e2099aa72050b5e00d01745153971e915fa190e4a86079a13ab8e73', 1, '', 'file01.txt', 0),
            ('982dfb44d32c54183e5399ae180a701d70c1434736645eea98c23e6a81b99d1b', 2, '', 'file02.txt', 0),
            ('ecefb01d5d2f2cce6d2f51257e4d17b480aec572496cb6b2136740704529f35f', 3, '', 'file05.txt', 0),
            ('78f690041494259dbb0ca8e890b9464599f5fc1eeaad20de7c4c16b7761c0039', 4, 'directory01', 'file03.txt', 0),
            ('90acddd186ee9932103da80265a716c2340cbaeeecaaa1da18b78d8e02f97e72', 5, 'directory01', 'file04.txt', 0),
            ('186bf48b6b0d045b57d29f6961eb7fd10710cfdcd745384ba0c8015e11eb2363', 6, 'directory02', 'file06.txt', 0),
            ('30273fefb11ee96b052b34051985952ff551b77bde97ba11c79b7b8ab3dc2a16', 7, 'directory02', 'file07.txt', 0),
            ('5491aedaa8d92e62f28117a5d5a751c31c917ed05ffd974cd433fd5a9834c554', 8, 'directory03', 'file08.txt', 0),
        ]
        copy_diff_csv = (
            'Переименовали,directory02/file06.txt,directory02/file06_renamed.txt,186bf48b6b0d045b57d29f6961eb7fd10710cfdcd745384ba0c8015e11eb2363,6\n'
        )
        origin_db_after_applying_diff = [
            ('4256508e9e2099aa72050b5e00d01745153971e915fa190e4a86079a13ab8e73', 1, '', 'file01.txt', 0),
            ('982dfb44d32c54183e5399ae180a701d70c1434736645eea98c23e6a81b99d1b', 2, '', 'file02.txt', 0),
            ('ecefb01d5d2f2cce6d2f51257e4d17b480aec572496cb6b2136740704529f35f', 3, '', 'file05.txt', 0),
            ('78f690041494259dbb0ca8e890b9464599f5fc1eeaad20de7c4c16b7761c0039', 4, 'directory01', 'file03.txt', 0),
            ('90acddd186ee9932103da80265a716c2340cbaeeecaaa1da18b78d8e02f97e72', 5, 'directory01', 'file04.txt', 0),
            ('186bf48b6b0d045b57d29f6961eb7fd10710cfdcd745384ba0c8015e11eb2363', 6, 'directory02', 'file06_renamed.txt', 0),
            ('30273fefb11ee96b052b34051985952ff551b77bde97ba11c79b7b8ab3dc2a16', 7, 'directory02', 'file07.txt', 0),
            ('5491aedaa8d92e62f28117a5d5a751c31c917ed05ffd974cd433fd5a9834c554', 8, 'directory03', 'file08.txt', 0),
        ]
        self.all_process(copy_fs, copy_db, copy_diff_csv, origin_db_after_applying_diff)

    def test_all_process_moved_file(self):
        copy_fs = (
            ('/copy/file01.txt', 'content01'),
            ('/copy/file02.txt', 'content02'),
            ('/copy/file05.txt', 'content05'),
            ('/copy/directory01/file03.txt', 'content03'),
            ('/copy/directory01/file04.txt', 'content04'),
            ('/copy/directory02_newdir/file06.txt', 'content06'),
            ('/copy/directory02/file07.txt', 'content07'),
            ('/copy/directory03/file08.txt', 'content08'),
        )
        copy_db = [
            ('4256508e9e2099aa72050b5e00d01745153971e915fa190e4a86079a13ab8e73', 1, '', 'file01.txt', 0),
            ('982dfb44d32c54183e5399ae180a701d70c1434736645eea98c23e6a81b99d1b', 2, '', 'file02.txt', 0),
            ('ecefb01d5d2f2cce6d2f51257e4d17b480aec572496cb6b2136740704529f35f', 3, '', 'file05.txt', 0),
            ('78f690041494259dbb0ca8e890b9464599f5fc1eeaad20de7c4c16b7761c0039', 4, 'directory01', 'file03.txt', 0),
            ('90acddd186ee9932103da80265a716c2340cbaeeecaaa1da18b78d8e02f97e72', 5, 'directory01', 'file04.txt', 0),
            ('186bf48b6b0d045b57d29f6961eb7fd10710cfdcd745384ba0c8015e11eb2363', 6, 'directory02', 'file06.txt', 0),
            ('30273fefb11ee96b052b34051985952ff551b77bde97ba11c79b7b8ab3dc2a16', 7, 'directory02', 'file07.txt', 0),
            ('5491aedaa8d92e62f28117a5d5a751c31c917ed05ffd974cd433fd5a9834c554', 8, 'directory03', 'file08.txt', 0),
        ]
        copy_diff_csv = (
            'Переместили,directory02/file06.txt,directory02_newdir/file06.txt,186bf48b6b0d045b57d29f6961eb7fd10710cfdcd745384ba0c8015e11eb2363,6\n'
        )
        origin_db_after_applying_diff = [
            ('4256508e9e2099aa72050b5e00d01745153971e915fa190e4a86079a13ab8e73', 1, '', 'file01.txt', 0),
            ('982dfb44d32c54183e5399ae180a701d70c1434736645eea98c23e6a81b99d1b', 2, '', 'file02.txt', 0),
            ('ecefb01d5d2f2cce6d2f51257e4d17b480aec572496cb6b2136740704529f35f', 3, '', 'file05.txt', 0),
            ('78f690041494259dbb0ca8e890b9464599f5fc1eeaad20de7c4c16b7761c0039', 4, 'directory01', 'file03.txt', 0),
            ('90acddd186ee9932103da80265a716c2340cbaeeecaaa1da18b78d8e02f97e72', 5, 'directory01', 'file04.txt', 0),
            ('186bf48b6b0d045b57d29f6961eb7fd10710cfdcd745384ba0c8015e11eb2363', 6, 'directory02_newdir', 'file06.txt', 0),
            ('30273fefb11ee96b052b34051985952ff551b77bde97ba11c79b7b8ab3dc2a16', 7, 'directory02', 'file07.txt', 0),
            ('5491aedaa8d92e62f28117a5d5a751c31c917ed05ffd974cd433fd5a9834c554', 8, 'directory03', 'file08.txt', 0),
        ]
        self.all_process(copy_fs, copy_db, copy_diff_csv, origin_db_after_applying_diff)

    def test_all_process_moved_and_renamed_file(self):
        copy_fs = (
            ('/copy/file01.txt', 'content01'),
            ('/copy/file02.txt', 'content02'),
            ('/copy/file05.txt', 'content05'),
            ('/copy/directory01/file03.txt', 'content03'),
            ('/copy/directory01/file04.txt', 'content04'),
            ('/copy/directory02_newdir/file06_renamed.txt', 'content06'),
            ('/copy/directory02/file07.txt', 'content07'),
            ('/copy/directory03/file08.txt', 'content08'),
        )
        copy_db = [
            ('4256508e9e2099aa72050b5e00d01745153971e915fa190e4a86079a13ab8e73', 1, '', 'file01.txt', 0),
            ('982dfb44d32c54183e5399ae180a701d70c1434736645eea98c23e6a81b99d1b', 2, '', 'file02.txt', 0),
            ('ecefb01d5d2f2cce6d2f51257e4d17b480aec572496cb6b2136740704529f35f', 3, '', 'file05.txt', 0),
            ('78f690041494259dbb0ca8e890b9464599f5fc1eeaad20de7c4c16b7761c0039', 4, 'directory01', 'file03.txt', 0),
            ('90acddd186ee9932103da80265a716c2340cbaeeecaaa1da18b78d8e02f97e72', 5, 'directory01', 'file04.txt', 0),
            ('186bf48b6b0d045b57d29f6961eb7fd10710cfdcd745384ba0c8015e11eb2363', 6, 'directory02', 'file06.txt', 0),
            ('30273fefb11ee96b052b34051985952ff551b77bde97ba11c79b7b8ab3dc2a16', 7, 'directory02', 'file07.txt', 0),
            ('5491aedaa8d92e62f28117a5d5a751c31c917ed05ffd974cd433fd5a9834c554', 8, 'directory03', 'file08.txt', 0),
        ]
        copy_diff_csv = (
            'Переместили и переименовали,directory02/file06.txt,directory02_newdir/file06_renamed.txt,186bf48b6b0d045b57d29f6961eb7fd10710cfdcd745384ba0c8015e11eb2363,6\n'
        )
        origin_db_after_applying_diff = [
            ('4256508e9e2099aa72050b5e00d01745153971e915fa190e4a86079a13ab8e73', 1, '', 'file01.txt', 0),
            ('982dfb44d32c54183e5399ae180a701d70c1434736645eea98c23e6a81b99d1b', 2, '', 'file02.txt', 0),
            ('ecefb01d5d2f2cce6d2f51257e4d17b480aec572496cb6b2136740704529f35f', 3, '', 'file05.txt', 0),
            ('78f690041494259dbb0ca8e890b9464599f5fc1eeaad20de7c4c16b7761c0039', 4, 'directory01', 'file03.txt', 0),
            ('90acddd186ee9932103da80265a716c2340cbaeeecaaa1da18b78d8e02f97e72', 5, 'directory01', 'file04.txt', 0),
            ('186bf48b6b0d045b57d29f6961eb7fd10710cfdcd745384ba0c8015e11eb2363', 6, 'directory02_newdir', 'file06_renamed.txt', 0),
            ('30273fefb11ee96b052b34051985952ff551b77bde97ba11c79b7b8ab3dc2a16', 7, 'directory02', 'file07.txt', 0),
            ('5491aedaa8d92e62f28117a5d5a751c31c917ed05ffd974cd433fd5a9834c554', 8, 'directory03', 'file08.txt', 0),
        ]
        self.all_process(copy_fs, copy_db, copy_diff_csv, origin_db_after_applying_diff)

    def test_all_process_moved_file_and_add_another_file_with_the_same_name(self):
        copy_fs = (
            ('/copy/file01.txt', 'content01'),
            ('/copy/file02.txt', 'content02'),
            ('/copy/file05.txt', 'content05'),
            ('/copy/directory01/file03.txt', 'content03'),
            ('/copy/directory01/file04.txt', 'content04'),
            ('/copy/directory02_newdir/file06.txt', 'content06'),
            ('/copy/directory02/file07.txt', 'content07'),
            ('/copy/directory03/file08.txt', 'content08'),
            ('/copy/directory02/file06.txt', 'content06_new'),
        )
        copy_db = [
            ('4256508e9e2099aa72050b5e00d01745153971e915fa190e4a86079a13ab8e73', 1, '', 'file01.txt', 0),
            ('982dfb44d32c54183e5399ae180a701d70c1434736645eea98c23e6a81b99d1b', 2, '', 'file02.txt', 0),
            ('ecefb01d5d2f2cce6d2f51257e4d17b480aec572496cb6b2136740704529f35f', 3, '', 'file05.txt', 0),
            ('78f690041494259dbb0ca8e890b9464599f5fc1eeaad20de7c4c16b7761c0039', 4, 'directory01', 'file03.txt', 0),
            ('90acddd186ee9932103da80265a716c2340cbaeeecaaa1da18b78d8e02f97e72', 5, 'directory01', 'file04.txt', 0),
            ('186bf48b6b0d045b57d29f6961eb7fd10710cfdcd745384ba0c8015e11eb2363', 6, 'directory02', 'file06.txt', 0),
            ('30273fefb11ee96b052b34051985952ff551b77bde97ba11c79b7b8ab3dc2a16', 7, 'directory02', 'file07.txt', 0),
            ('5491aedaa8d92e62f28117a5d5a751c31c917ed05ffd974cd433fd5a9834c554', 8, 'directory03', 'file08.txt', 0),
            ('479f8b5f18b1d568c81055c22b1f9d390c3c6d4618a8065cae0fa767fb3e580c', 9, 'directory02', 'file06.txt', 0),
        ]
        copy_diff_csv = (
            'Переместили,directory02/file06.txt,directory02_newdir/file06.txt,186bf48b6b0d045b57d29f6961eb7fd10710cfdcd745384ba0c8015e11eb2363,6\n'
            'Новый,,directory02/file06.txt,479f8b5f18b1d568c81055c22b1f9d390c3c6d4618a8065cae0fa767fb3e580c,9\n'
        )
        origin_db_after_applying_diff = [
            ('4256508e9e2099aa72050b5e00d01745153971e915fa190e4a86079a13ab8e73', 1, '', 'file01.txt', 0),
            ('982dfb44d32c54183e5399ae180a701d70c1434736645eea98c23e6a81b99d1b', 2, '', 'file02.txt', 0),
            ('ecefb01d5d2f2cce6d2f51257e4d17b480aec572496cb6b2136740704529f35f', 3, '', 'file05.txt', 0),
            ('78f690041494259dbb0ca8e890b9464599f5fc1eeaad20de7c4c16b7761c0039', 4, 'directory01', 'file03.txt', 0),
            ('90acddd186ee9932103da80265a716c2340cbaeeecaaa1da18b78d8e02f97e72', 5, 'directory01', 'file04.txt', 0),
            ('186bf48b6b0d045b57d29f6961eb7fd10710cfdcd745384ba0c8015e11eb2363', 6, 'directory02_newdir', 'file06.txt', 0),
            ('30273fefb11ee96b052b34051985952ff551b77bde97ba11c79b7b8ab3dc2a16', 7, 'directory02', 'file07.txt', 0),
            ('5491aedaa8d92e62f28117a5d5a751c31c917ed05ffd974cd433fd5a9834c554', 8, 'directory03', 'file08.txt', 0),
            ('479f8b5f18b1d568c81055c22b1f9d390c3c6d4618a8065cae0fa767fb3e580c', 9, 'directory02', 'file06.txt', 0),
        ]
        self.all_process(copy_fs, copy_db, copy_diff_csv, origin_db_after_applying_diff)
