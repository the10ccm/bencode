""" Torrent File Parser
"""
import argparse
import logging
import os
import re
import sys


resume_dir = "Resume"
torrents_dir = "Torrents"


def decode_bencode(body):
    """Parse bencoded string
        Parameters:
            bytearray: torrent file content
        Returns:
            dict: structured data
    """
    if body[0] == ord('i'):
        # integer 'i..e'
        # We leave an ability to raise AttributeError if a number was not found
        value, body[:] = re.search(
            rb'^i(?P<value>-?\d+)e(?P<body>.*)',
            body,
            re.DOTALL).group('value', 'body')
        logging.debug('integer: %s' % value)
        return int(value)
    elif 0x30 <= body[0] <= 0x39:
        # string 'number:string'
        number, body[:] = re.search(
            rb'^(?P<number>\d+):(?P<body>.*)',
            body,
            re.DOTALL).group('number', 'body')
        value, body[:] = body[:int(number)], body[int(number):]
        logging.debug('str: %s' % value)
        return value
    elif body[0] == ord('l'):
        # list 'l..e'
        belist = []
        del body[0]
        while True:
            value = decode_bencode(body)
            if value is None:
                break
            belist.append(value)
        logging.debug('list: %s' % belist)
        return belist
    elif body[0] == ord('d'):
        # dict 'd..e'
        bedict = {}
        del body[0]
        while True:
            key = decode_bencode(body)
            #print('key', key)
            if key is None:
                break
            value = decode_bencode(body)
            if value is None:
                raise ValueError('Key value is None')
            bedict[key.decode()] = value
        logging.debug('dict: %s' % bedict)
        return bedict
    # encountered closing token 'e'
    del body[0]
    logging.debug('closing token')
    return None


def parse_resume(filename):
    """Parse Resume Files
    """
    value = None
    content = bytearray()
    with open(filename, mode='rb') as f:
        while True:
            chunk = f.read()
            if not chunk:
                break
            content += chunk
    value = decode_bencode(content)
    return value


if __name__ == '__main__':
    #torrent = parse_resume('/Users/<user>/Library/Application Support/Transmission/Resume/94cb260e0e5ce0485f2f4e1aa632d43380b19794.resume')
    parser = argparse.ArgumentParser(prog=sys.argv[0])
    parser.add_argument('--debug', help='Verbose debug', action='store_const',
        const=True, default=False)
    parser.add_argument('path', help='The path to the Transmission working directory')
    args = parser.parse_args()

    if args.debug:
        logging.basicConfig(level=logging.DEBUG)
    resume_basepath = os.path.join(args.path, resume_dir)
    torrents_basepath = os.path.join(args.path, torrents_dir)
    r_entries = os.listdir(resume_basepath)
    t_entries = os.listdir(torrents_basepath)

    for entry in r_entries:
        if entry.endswith('.resume') and "%s%s" % (entry[:-7], '.torrent') not in t_entries:
            logging.debug('resume filename: %s' % entry)
            # Ruseme filename hash does not present in the Torrents dir
            torrent = parse_resume(os.path.join(resume_basepath, entry))
            print(torrent['name'].decode('utf-8'))


