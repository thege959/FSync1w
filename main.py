import logging
import filecmp
import datetime as dt
import argparse
import os
import shutil
import time


def get_folder_content(folderpath):
    """
    Gets content of folder recursively.

    :param folderpath: path of folder to be scanned
    :return: list of DirEntry objects
    """
    f = [os.path.relpath(folderpath)]

    for entity in os.scandir(folderpath):
        if entity.is_dir():
            f += get_folder_content(entity)
        elif entity.is_file():
            f.append(os.path.relpath(entity))

    return f


def analyze_content_difference(src_entities, dst_entities):
    print('raw data:')
    print(src)
    print(dst)
    # Separating dirs and files
    src_files, src_dirs = _get_dir_files_relpath(src_entities)
    dst_files, dst_dirs = _get_dir_files_relpath(dst_entities)

    # Clasifying dirs and files as new, old and same based on name
    new_files, same_files, old_files = clasify_items(src_files, dst_files)
    new_dirs, _, old_dirs = clasify_items(src_dirs, dst_dirs)

    modified_files = check_for_updates(src_entities[0],dst_entities[0],same_files)

    return new_dirs, old_dirs, new_files, modified_files, old_files


def clasify_items(entities_src, entities_dst):
    set_src = set(entities_src)
    set_dst = set(entities_dst)
    new_entities = list(set_src - set_dst)
    print('NEW entities:')
    print(new_entities)

    same_entities = list(set_src & set_dst)
    print('SAME entities:')
    print(same_entities)

    old_entities = list(set_dst - set_src)
    print('OLD entities:')
    print(old_entities)
    return new_entities, same_entities, old_entities


def clean_old_dirs(dst_root, ofiles, odirs):

    # deleting OLD folders
    odirs.sort(key=lambda x: -x.count('/'))  # sorting to respect folder hierarchy for deleting
    print('Deleting OLD folders:')
    for d in odirs:
        print(f"    {dst_root + d}")
        shutil.rmtree(dst_root + d)
    print('Done.')

    # deleting OLD files
    print('Deleting remainig OLD files:')
    for f in ofiles:
        if os.path.exists(dst_root + f):
            print(f"    {dst_root + f}")
            os.remove(dst_root + os.path.dirname(f) + f)
    print('Done.')


def create_new_folders(dst_root, ndirs):
    ndirs.sort(key=lambda x: x.count('/'))  # sorting to respect folder hierarchy for creating
    print('Creating new folders:')
    for d in ndirs:
        print(f"    {dst_root + d}")
        os.mkdir(dst_root + d)
    print('Done.')


def copy_files(src_root, dst_root, nfiles):
    # copy new files
    print('Copying new files:')
    for f in nfiles:
        print(f"    {src_root + f}")
        shutil.copy2(src_root + f, dst_root + os.path.dirname(f))
    print('Done.')


def check_for_updates(src_root, dst_root,same_file_list):
    modified_files = []
    print('Checking for modified files..')
    for f in same_file_list:
        src_file = src_root + f
        dst_file = dst_root + f
        if not filecmp.cmp(src_file,dst_file):
            modified_files.append(f)
    print(f'Found {len(modified_files)} files modified.')
    return modified_files


def _get_dir_files_relpath(entities_list):
    root_folder = entities_list[0]
    files = [ent[len(root_folder):] for ent in entities_list[1:] if os.path.isfile(ent)]
    dirs = [ent[len(root_folder):] for ent in entities_list[1:] if os.path.isdir(ent)]
    return files, dirs


if __name__ == '__main__':
    # Setting up an argument parser
    parser = argparse.ArgumentParser(description='Synchronize 2 folders')
    parser.add_argument('-src', type=str, required=True,
                        dest='src',
                        help='SOURCE folder')
    parser.add_argument('-dst', type=str, required=True,
                        dest='dst',
                        help='DESTINATION folder')
    parser.add_argument('-t', type=int, default=None,
                        dest='interval',
                        help='interval in seconds')
    parser.add_argument('-log', type=str, dest='logfile',required=True,
                        help='interval in seconds')

    args = parser.parse_args()
    # Setting up the logger
    logging.basicConfig(level=logging.DEBUG,
                        format='%(asctime)s %(name)-12s %(levelname)-8s %(message)s',
                        datefmt='%m-%d %H:%M',
                        filename=args.logfile,
                        filemode='w')

    given_interval = args.interval if args.interval else 0
    # Starting the main process
    while True:
        tstart = dt.datetime.now()
        tnext = tstart + dt.timedelta(seconds=given_interval)

        # Getting folders content raw info
        src = get_folder_content(args.src)
        dst = get_folder_content(args.dst)

        # Analyzing what needs to be updated
        new_dirs, old_dirs, new_files, modified_files, old_files = analyze_content_difference(src, dst)

        # Starting the update
        clean_old_dirs(args.dst, old_files, old_dirs)
        create_new_folders(args.dst, new_dirs)
        copy_files(args.src, args.dst, new_files)
        copy_files(args.src, args.dst, modified_files)

        if given_interval == 0:
            break
        else:
            remaining_interval = (tnext - dt.datetime.now()).total_seconds()
            print(remaining_interval)
            if remaining_interval > 0:
                time.sleep(remaining_interval)

