import os
from unittest import TestCase
from unittest.mock import patch

from library_storage import LibraryStorage

TEMP_DIRECTORY = os.path.expandvars(os.path.join('%TEMP%', 'test_library_storage'))


def create_test_origin_library(library_path):
    with open(os.path.join(library_path, 'file01.txt'), 'w') as test_file:
        test_file.write('content01')

    with open(os.path.join(library_path, 'file02.txt'), 'w') as test_file:
        test_file.write('content02')

    with open(os.path.join(library_path, 'file05.txt'), 'w') as test_file:
        test_file.write('content05')

    os.makedirs(os.path.join(library_path, 'directory01'))
    with open(os.path.join(library_path, 'directory01', 'file03.txt'), 'w') as test_file:
        test_file.write('content03')

    with open(os.path.join(library_path, 'directory01', 'file04.txt'), 'w') as test_file:
        test_file.write('content04')

    os.makedirs(os.path.join(library_path, 'directory02'))
    with open(os.path.join(library_path, 'directory02', 'file06.txt'), 'w') as test_file:
        test_file.write('content06')

    with open(os.path.join(library_path, 'directory02', 'file07.txt'), 'w') as test_file:
        test_file.write('content07')

    os.makedirs(os.path.join(library_path, 'directory03'))
    with open(os.path.join(library_path, 'directory03', 'file08.txt'), 'w') as test_file:
        test_file.write('content08')


@patch('library_storage.TEMP_DIRECTORY', TEMP_DIRECTORY)
class CoreTestCase(TestCase):

    @classmethod
    def setUpClass(cls) -> None:
        cls.repository_path = os.path.dirname(os.path.dirname(__file__))
        cls.library_path = os.path.join(TEMP_DIRECTORY, 'origin')
        cls.library_path_changed = os.path.join(cls.repository_path, 'example_library_changed')
        cls.csv_path = os.path.join(cls.repository_path, 'example_csv')
        cls.diff_path = os.path.join(cls.repository_path, 'example_diff')
        cls.diff_file_path = os.path.join(cls.diff_path, 'example_diff.zip')
        cls.db_path = ':memory:'

        if not os.path.exists(TEMP_DIRECTORY):
            os.mkdir(TEMP_DIRECTORY)

        if not os.path.exists(cls.library_path):
            os.mkdir(cls.library_path)

        create_test_origin_library(cls.library_path)
        cls.lib_storage = LibraryStorage(
            library_path=cls.library_path,
            csv_path=cls.csv_path,
            db_path=cls.db_path,
            diff_path=cls.diff_path,
            diff_file_path=cls.diff_file_path
        )

    @classmethod
    def tearDownClass(cls) -> None:
        cls.lib_storage.__exit__(None, None, None)
        os.unlink(TEMP_DIRECTORY)

    def test_scan_to_db(self):
        ...
