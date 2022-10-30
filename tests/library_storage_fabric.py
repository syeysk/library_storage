import os.path
import random


class LibraryStorageFabric:
    hashes = {}

    def __init__(self, fs):
        self.fs = fs
        self.db = []

    @classmethod
    def generate_hash(cls, file_content):
        if file_content not in cls.hashes:
            cls.hashes[file_content] = ''.join(random.sample('0123456789abcdef'*4, 64))

        return cls.hashes[file_content]

    # def add_file_into_db(self, file_path, file_content, is_deleted):

    def generate_db(self, excludes=None, is_deleted=0):
        if excludes is None:
            excludes = []

        bias = 0
        for file_id, (file_path, file_content) in enumerate(self.fs, 1):
            if file_path in excludes:
                bias += 1
                continue

            self.db.append(
                (
                    self.generate_hash(file_content),
                    file_id - bias,
                    os.path.dirname(file_path)[1:],
                    os.path.basename(file_path),
                    is_deleted,
                )
            )
