""" Processing Transmission torrents
    Transmission uses Transfers.plist for storing processed torrents
"""

import argparse
import logging
import os
import plistlib
import shutil
import sys

import bencode


TRANSFERS_PLIST = 'Transfers.plist'
TORRENTS_DIR = "Torrents"

logging.getLogger(name=__name__)
logging.basicConfig(format='%(levelname)s:%(message)s', level=logging.INFO)


class TransferError(Exception):
    pass

def get_transfers(filename):
    """Get torrents from Transfers.plist
    """
    try:
        with open(filename, 'rb') as fp:
            _root_object = plistlib.load(fp, fmt=plistlib.FMT_XML)
    except FileNotFoundError as m:
        logging.error("Transfers.plist does not exist. %s", m)
        sys.exit()
    return _root_object

def store_transfers(value, filename):
    """Save Transfers.plist
    """
    with open(filename, 'wb') as fp:
        root_object = plistlib.dump(value, fp, fmt=plistlib.FMT_XML)

def filter_transfers(root_object, field, value):
    """ Filter transfer by a field value, alternated root object
        Output:
            iltered files
    """
    _filtered_transfers = []
    root_object[:] = sorted(root_object, key=lambda x: x[field])
    started = False
    index = 0
    logging.info("Start filtering")
    while index < len(root_object) and root_object:
        torrent = root_object[index]
        if torrent[field] == value:
            _filtered_transfers.append(torrent)
            # cleanup filtered
            root_object.pop(index)
            started = True
        elif started:
            # Break as soon as the condition will be passed
            break
        else:
            index += 1
    return _filtered_transfers

def move_transfers(_transfer, dest_path, _mode):
    try:
        hashed_filename_path = _transfer['InternalTorrentPath']
    except KeyError as m:
        logging.warning("The transfer has a malformed structure")
        raise TransferError
    except TypeError as m:
        print(_transfer, m)
        raise TransferError
    bencode_object = bencode.parse_bencode(hashed_filename_path)
    if not bencode_object:
        raise TransferError
    try:
        # Get a symbolic filename
        bencode_info = bencode_object['info']
        if 'name.utf-8' in bencode_info:
            filename = bencode_info['name.utf-8'].decode()
        else:
            filename = bencode_info['name'].decode()
    except UnicodeDecodeError as m:
        logging.error("Torrent file '%s' did not decode its name '%s'",
                      hashed_filename_path,
                      bencode_object['info']['name'])
        sys.exit()
    if not filename:
        logging.error(f"The symbolic filename is empty for {hashed_filename_path}")
        raise TransferError
    if not hasattr(move_transfers, 'exist'):
        move_transfers.exist = set()
    # add a hash to the end of file name to create a uniq filename
    if filename in move_transfers.exist:
        filename += "-%s" % _transfer['TorrentHash']
    move_transfers.exist.add(filename)
    filename_path = os.path.join(dest_path, filename+'.torrent')
    try:
        if _mode == 'copy':
            shutil.copy(hashed_filename_path, filename_path)
        elif _mode == 'move':
            shutil.move(hashed_filename_path, filename_path)
    except IOError as m:
        logging.error("'%s' is not transfered to '%s': %s",
                      hashed_filename_path, filename_path, m)
        sys.exit()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(prog=sys.argv[0])
    parser.add_argument('--debug', help='Verbose debug', action='store_const',
                        const=True, default=False)
    parser.add_argument('--update-plist', help='Update Transfers.plistlib', action='store_const',
                        const=True, default=False)
    parser.add_argument('--mode', help='Mode: move|copy|simulate(default)',
                        choices=['move', 'copy', 'simulate'],
                        default='simulate')
    parser.add_argument('-g', '--group', help='Group Value',
                        type=int, required=True)
    parser.add_argument('path', help='A path to the Transmission working directory')
    parser.add_argument('dest_path', help='A target path for moving the filtered torrents')
    args = parser.parse_args()
    GROUP_VALUE = 12

    if args.debug:
        logging.basicConfig(level=logging.DEBUG)
    if not os.path.isdir(args.path):
        logging.error("The source path '%s' does not exist", args.path)
        sys.exit()
    if not os.path.isdir(args.dest_path):
        logging.error("The destination path '%s' does not exist", args.dest_path)
        sys.exit()
    torrents_basepath = os.path.join(args.path, TORRENTS_DIR)
    #t_entries = os.listdir(torrents_basepath)
    transfers_plist = os.path.join(args.path, TRANSFERS_PLIST)

    root_object = get_transfers(transfers_plist)
    filtered_transfers = filter_transfers(root_object, 'GroupValue', args.group)

    logging.info("Start moving")
    counter = 0
    # get the filtered torrent files and move them to the destination path
    for transfer in filtered_transfers:
        try:
            move_transfers(transfer, args.dest_path, args.mode)
        except TransferError:
            continue
        counter += 1

    # Store transfers.plist after the modification
    logging.info("Store plist")
    logging.debug("Transfers: %s" % root_object)
    dest_plist = os.path.join(args.dest_path, TRANSFERS_PLIST)
    if args.update_plist:
        store_transfers(root_object, dest_plist)
    else:
        print("Transfers.plist has not been updated. Use an --update-plist option to write changes.")
    if args.mode == 'simulate':
        print("Files have not been moved in the simulate mode. Change the transfer files mode by a --mode option")
    print("Files transfered: %s " % (counter,))



