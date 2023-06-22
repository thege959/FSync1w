import unittest
import os
from random import randint
import shutil
import fsync1w


def _create_folder_structure():
    # creating random folder structure
    print('Setting up the folders')
    shutil.rmtree('./FA/')
    os.mkdir('./FA/')
    nd = randint(5, 10)  # number of folders to create
    nft = 0  # total number of files created
    for _ in range(nd):
        dname = ''.join([chr(randint(97, 117)) for _ in range(5)])
        os.mkdir('./FA\\' + dname + '\\')
        nf = randint(1, 15)  # number of files to create
        nft += nf
        for _ in range(nf):
            fname = ''.join([chr(randint(97, 117)) for _ in range(8)])
            with open('./FA\\' + dname + '\\' + fname + '.txt', 'w') as file:
                txt = ''.join([chr(randint(65, 120)) for _ in range(100)])
                file.write(txt)

    shutil.rmtree('./FB/')
    os.mkdir('./FB/')
    return nd, nft


class xtest(unittest.TestCase):
    def setUp(self) -> None:
        nd, nft = _create_folder_structure()

        self.nd = nd
        self.nft = nft

    def test_number_of_dirs(self):
        entities = fsync1w.get_folder_content('./FA/')
        files, dirs = fsync1w._get_dir_files_relpath(entities)
        self.assertEqual(self.nd, len(dirs))

    def test_number_of_files(self):
        entities = fsync1w.get_folder_content('./FA/')
        files, dirs = fsync1w._get_dir_files_relpath(entities)
        self.assertEqual(self.nft, len(files))


