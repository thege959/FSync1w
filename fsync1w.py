import logging
import filecmp
import datetime as dt
import argparse
import os
import shutil
import time
stages = {0: 'INITIALIZING',
          1: 'SCANNING', 2: 'ANALYZING',
          3: 'DELETING', 4: 'CREATING', 5: 'COPYING',
          8: 'SUMMARY', 9: 'FINALIZING'}


def parse_cli_arguments():
    """
    Set up the Argument Parser object.

    :return: ArgumentParser object
    """
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
    parser.add_argument('-log', type=str, dest='logfile', required=True,
                        help='interval in seconds')
    cli_args = parser.parse_args()

    # Perform checks on src and dst
    if not os.path.exists(cli_args.src):
        parser.error(f'Source folder {cli_args.src} does not exist!')
        return None

    if not os.path.exists(cli_args.dst):
        parser.error(f'Destination folder {cli_args.dst} does not exist!')
        return None

    if os.path.exists(cli_args.logfile):
        print(f'Log file {cli_args.logfile} already exists and will be overwritten!)')
        print('Continue?(y/n) ', end='')
        opt = input().lower()
        if opt == 'n':
            exit('Bye!')
        elif opt == 'y':
            os.remove(cli_args.logfile)
        else:
            parser.exit(-1, 'Wrong answer given!',)

    return cli_args


def define_logger():
    """
    Set up the Logger object.

    :return:  Logger object
    """
    # format for output file
    file_fmtstr = '%(asctime)s | %(name)-10s | STEP: %(step)-3s | %(stage)-13s: %(message)s'
    # format for console
    console_fmtstr = '%(asctime)s | %(name)-10s | STEP: %(step)-3s | %(stage)-13s: %(message)s'
    # date format
    datefmt = '%m-%d-%Y %H:%M:%S'

    logging.basicConfig(level=logging.INFO,
                        format=file_fmtstr,
                        datefmt=datefmt,
                        filename=args.logfile,
                        filemode='w')

    console_output = logging.StreamHandler()
    console_format = logging.Formatter(fmt=console_fmtstr, datefmt=datefmt)
    console_output.setFormatter(console_format)

    new_logger = logging.getLogger('')
    new_logger.addHandler(console_output)

    return new_logger


def get_folder_content(folderpath):
    """
    Gets content of folder recursively.

    :param folderpath: path of folder to be scanned
    :return: list of paths to files and folders relative to current working directory.
            First item is the origin folder.
    """
    f = [os.path.relpath(folderpath)]
    for entity in os.scandir(folderpath):
        if entity.is_dir():
            f += get_folder_content(entity)
        elif entity.is_file():
            f.append(os.path.relpath(entity))

    return f


def analyze_content_difference(src_entities, dst_entities, extra=None):
    """
    Analyzes the differences between the two list of relative paths
    returned by get_folder_content().

    :param src_entities: list of relative paths(string) to SOURCE files and folders
    :param dst_entities: list of relative paths(string) to DESTINATION files and folders
    :param extra: dictionary with extra information for logging purposes
    :return: separate lists of files and folders, clasified as new, old or
             same(from path perspective)
    """
    if not extra:
        extra = {'stage': '', 'step': ''}

    # Separating dirs and files
    src_files, src_dirs = _get_dir_files_relpath(src_entities)
    dst_files, dst_dirs = _get_dir_files_relpath(dst_entities)

    # Clasifying dirs and files as new, old and same based on name
    logger.info('Analyzing changes..', extra=extra)
    nfiles, same_files, ofiles = clasify_items(src_files, dst_files)
    ndirs, _, odirs = clasify_items(src_dirs, dst_dirs)

    logger.info('Found:', extra=extra)
    logger.info(f'\t\t{len(nfiles)} NEW files:', extra=extra)
    logger.info(f'\t\t{len(ndirs)} NEW dirs:', extra=extra)
    logger.info(f'\t\t{len(ofiles)} OLD files:', extra=extra)
    logger.info(f'\t\t{len(odirs)} OLD dirs:', extra=extra)
    logger.info(f'\t\t{len(same_files)} SAME files:', extra=extra)

    # checking files with the same path if they are modified
    mod_files = check_for_updates(src_entities[0], dst_entities[0], same_files, extra=extra)

    return ndirs, odirs, nfiles, mod_files, ofiles


def check_for_updates(src_root, dst_root, same_file_list, extra=None):
    """
    Compares files with same name and relative path (same_file_list)
     from source root folder (src_root) and destination root folder(dst_root)

    :param src_root: SOURCE root folder
    :param dst_root: DESTINATION root folder
    :param same_file_list: list of files to the compared
    :param extra: dictionary with extra information for logging purposes
    :return: list of MODIFIED files only.
    """
    # Defining extra information for logging purposes
    if not extra:
        extra = {'stage': '', 'step': ''}

    mod_files = []
    if same_file_list:
        logger.info('Checking for MODIFIED files:', extra=extra)
        for f in same_file_list:
            src_file = src_root + f
            dst_file = dst_root + f
            if not filecmp.cmp(src_file, dst_file):
                mod_files.append(f)
        logger.info(f'\t\tFound {len(mod_files)} files modified.', extra=extra)
        for f in mod_files:
            logger.info(f"        {src_root + f}", extra=extra)
    else:
        logger.info(f'No SAME files to check!', extra=extra)
    return mod_files


def clasify_items(entities_src, entities_dst):
    """
    Clasifies items(files or folders) as NEW, OLD or SAME based on
    their path(string) info.

    :param entities_src: list of SOURCE items(files or folders) as strings
    :param entities_dst: list of DESTINATION items(files or folders) as strings
    :return: separate lists of items(files or folders), clasified as:
            NEW, OLD or SAME(from path perspective)
    """
    set_src = set(entities_src)
    set_dst = set(entities_dst)

    new_entities = list(set_src - set_dst)
    same_entities = list(set_src & set_dst)
    old_entities = list(set_dst - set_src)

    return new_entities, same_entities, old_entities


def clean_old_dirs_files(dst_root, ofiles, odirs, extra=None):
    """
    Deletes files(ofiles) and folders(odirs) from root path(dst_root).

    :param dst_root: DESTINATION root folder
    :param ofiles: list of OLD files to be deleted
    :param odirs: list of OLD folders to be deleted
    :param extra: dictionary with extra information for logging purposes
    :return: None
    """
    if not extra:
        extra = {'stage': '', 'step': ''}
    d_err_cnt = 0
    # deleting OLD folders
    if odirs:
        odirs.sort(key=lambda x: -x.count('/'))  # sorting to respect folder hierarchy for deleting
        logger.info('Deleting OLD folders:', extra=extra)
        for d in odirs:
            logger.info(f"    {dst_root + d}", extra=extra)
            try:
                shutil.rmtree(dst_root + d)
            except OSError as e:
                d_err_cnt += 1
                logger.info(f"ERROR encountered when deleting {dst_root + d}", extra=extra)
                logger.info(f"ERROR message: {e}", extra=extra)
        logger.info('Done!', extra=extra)
    else:
        logger.info('No OLD folders to delete!', extra=extra)

    # deleting OLD files
    f_err_cnt = 0
    if ofiles:
        logger.info('Deleting remainig OLD files:', extra=extra)
        for f in ofiles:
            if os.path.exists(dst_root + f):
                logger.info(f"    {dst_root + f}", extra=extra)
                try:
                    os.remove(dst_root + f)
                except OSError as e:
                    f_err_cnt += 1
                    logger.info(f"ERROR encountered when deleting {dst_root + f}", extra=extra)
                    logger.info(f"ERROR message: {e}", extra=extra)
        logger.info('Done!', extra=extra)
    else:
        logger.info('No OLD files to delete!', extra=extra)

    return d_err_cnt, f_err_cnt


def create_new_folders(dst_root, ndirs,  extra=None):
    """
    Creates NEW folders(ndirs) in root path(dst_root).

    :param dst_root: DESTINATION root folder
    :param ndirs: list of NEW folders to be created
    :param extra: dictionary with extra information for logging purposes
    :return: None
    """
    if not extra:
        extra = {'stage': '', 'step': ''}

    # Creating NEW folders
    if ndirs:
        ndirs.sort(key=lambda x: x.count('/'))  # sorting to respect folder hierarchy for creating
        logger.info('Creating NEW folders:', extra=extra)
        for d in ndirs:
            logger.info(f"    {dst_root + d}", extra=extra)
            os.mkdir(dst_root + d)
        logger.info('Done!', extra=extra)
    else:
        logger.info('No NEW folders to create!', extra=extra)


def copy_files(src_root, dst_root, nfiles, kind, extra=None):
    """
    Copies files(nfiles) from SOURCE root path(src_root) to
    DESTINATION root path(dst_root).

    :param src_root: SOURCE root folder
    :param dst_root: DESTINATION root folder
    :param nfiles: list of files to the copied
    :param kind: type of files: NEW or MODIFIED, used in logging information
    :param extra: dictionary with extra information for logging purposes
    :return: number of OSError exceptions encountered. 0 = no expections
    """
    # Defining extra information for logging purposes
    if not extra:
        extra = {'stage': '', 'step': ''}
    err_cnt = 0
    # Copying NEW/MODIFIED files
    if nfiles:
        logger.info(f'Copying {kind} files:', extra=extra)
        for f in nfiles:
            logger.info(f"    {src_root + f}", extra=extra)
            try:
                shutil.copy2(src_root + f, dst_root + os.path.dirname(f))
            except OSError as e:
                err_cnt += 1
                logger.info(f"ERROR encountered when copying {src_root + f}", extra=extra)
                logger.info(f"ERROR message: {e}", extra=extra)

        logger.info(f'Done', extra=extra)
    else:
        logger.info(f'No {kind} files to copy!', extra=extra)

    return err_cnt


def summarize(start_time, filestats, errstats, extra=None):
    """
    Summarizes the last synchornization step.


    :param start_time: datetime object created at the start of the synchornization step
    :param filestats: list of lengths of the lists containing:
        - new files, new folders, old files, old folders, modified files
    :param errstats: list of error counters for the same categories
    :param extra: dictionary with extra information for logging purposes
    :return: None
    """
    if not extra:
        extra = {'stage': '', 'step': ''}

    now = dt.datetime.now()
    logger.info(f'Process duration: {(now-start_time).total_seconds()} seconds', extra=extra)
    logger.info(f'\t\tDeleted: {filestats[2]-errstats[2]} files ({errstats[2]} errors)', extra=extra)
    logger.info(f'\t\tDeleted: {filestats[3] - errstats[3]} folders ({errstats[3]} errors)', extra=extra)
    logger.info(f'\t\tCopied: {filestats[0] - errstats[0]} files ({errstats[0]} errors)', extra=extra)
    logger.info(f'\t\tCopied: {filestats[1]} folders', extra=extra)
    logger.info(f'\t\tUpdated: {filestats[4] - errstats[4]} files ({errstats[4]} errors)', extra=extra)


def _get_dir_files_relpath(entities_list):
    """ Utility function to obtain paths relative to the root path provided in first element

    :param entities_list: list of paths to files and folders relative to working directoru.
                          First item is the origin folder.
    :return: list of files and folders relative to origin folder
    """
    root_folder = entities_list[0]
    files = [ent[len(root_folder):] for ent in entities_list[1:] if os.path.isfile(ent)]
    dirs = [ent[len(root_folder):] for ent in entities_list[1:] if os.path.isdir(ent)]
    return files, dirs


if __name__ == '__main__':

    # parsing CLI arguments
    args = parse_cli_arguments()

    # creating a logger object
    logger = define_logger()

    given_interval = args.interval if args.interval else 0

    # Starting the main process
    stp_cnt = 0
    # Defining extra information for logging purposes
    ext = {'stage': stages[0], 'step': 'N/A'}
    logger.info('Starting MAIN synchronization loop', extra=ext)

    while True:
        stp_cnt += 1
        ext = {'stage': stages[0], 'step': stp_cnt}

        # keeping starting time of the current synchronization step
        tstart = dt.datetime.now()
        # calculating starting time for next synchronization step
        tnext = tstart + dt.timedelta(seconds=given_interval)

        logger.info('{:*^50}'.format(f'  STEP: {stp_cnt}  '), extra=ext)
        logger.info('Synchronization STEP: started!', extra=ext)

        # Getting folders content raw info
        ext['stage'] = stages[1]
        logger.info(f'Scanning folder {args.src}', extra=ext)
        src = get_folder_content(args.src)
        logger.info(f'\t\tFound: {len(src)-1} files and folders', extra=ext)

        logger.info(f'Scanning folder {args.dst}', extra=ext)
        dst = get_folder_content(args.dst)
        logger.info(f'\t\tFound: {len(dst)-1} files and folders', extra=ext)

        # Analyzing what needs to be updated
        ext['stage'] = stages[2]
        new_dirs, old_dirs, new_files, modified_files, old_files = analyze_content_difference(src, dst, ext)

        # Starting the update
        ext['stage'] = stages[3]
        ddel_error_cnt, fdel_error_cnt = clean_old_dirs_files(args.dst, old_files, old_dirs, ext)
        ext['stage'] = stages[4]
        create_new_folders(args.dst, new_dirs, ext)
        ext['stage'] = stages[5]
        n_error_cnt = copy_files(args.src, args.dst, new_files, kind='NEW', extra=ext)
        m_error_cnt = copy_files(args.src, args.dst, modified_files, kind='MODIFIED', extra=ext)

        file_stats = [len(ent_list) for ent_list in [new_files, new_dirs, old_files, old_dirs, modified_files]]
        err_stats = [n_error_cnt, 0, fdel_error_cnt, ddel_error_cnt, m_error_cnt]

        ext['stage'] = stages[8]
        summarize(tstart, file_stats, err_stats, extra=ext)

        ext['stage'] = stages[9]
        err_msg = 'SUCCESSFULLY'
        if sum(err_stats) > 0:
            err_msg = f'with {sum(err_stats)} error(s)!'

        logger.info(f'Synchronization STEP: finished {err_msg}!', extra=ext)

        # checking if interval was given and if yes, how much time until next synchronization
        if given_interval == 0:
            break
        else:
            remaining_interval = (tnext - dt.datetime.now()).total_seconds()
            logger.info(f'Time until next synchronization step: {round(remaining_interval, 0)} seconds',
                        extra=ext)
            logger.info('{:*^50}'.format(f'  STEP: {stp_cnt} \n'), extra=ext)

            if remaining_interval > 0:
                time.sleep(remaining_interval)
            else:
                logger.warning('\tWARNING!!!', extra=ext)
                logger.warning('Last synchronization did not finish before'
                               ' next synchronization was supposed to start!!!', extra=ext)
                logger.warning('\tWARNING', extra=ext)
