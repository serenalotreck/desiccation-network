"""
Pre-process the XML dataset to get a mapping between files and UIDs

Author: Serena G. Lotreck
"""
import argparse
from os.path import abspath, splitext
from os import listdir
from tqdm import tqdm
from lxml import etree
import json


def get_uids(xml):
    """
    Get the UIDs present in a dataset.

    parameters:
        xml, ElementTree: dataset to parse

    returns:
        uids, list of str: UIDs
    """
    uids = []
    for record in xml.getroot():
        for uid in record.findall('{http://clarivate.com/schema/wok5.30/public/FullRecord}UID'):
            uids.append(uid.text)

    return uids


def main(dataset_dir, output_json):

    print('\nGetting UID map...')
    uid_map = {}
    for f in tqdm(listdir(dataset_dir)):
        if splitext(f)[1] == '.xml':
            tree = etree.parse(f'{dataset_dir}/{f}')
            uids = get_uids(tree)
            for uid in uids:
                uid_map[uid] = f
            del tree

    print('\nSaving...')
    with open(output_json, 'w') as myf:
        json.dump(uid_map, myf)

    print(f'Saved output as {output_json}')

    print('\nDone!')


if __name__ == "__main__":

    parser = argparse.ArgumentParser(description='Get XML UID mapping')

    parser.add_argument('dataset_dir', type=str,
            help='Dataset to parse')
    parser.add_argument('output_json', type=str,
            help='Path to save output')

    args = parser.parse_args()

    args.dataset_dir = abspath(args.dataset_dir)
    args.output_json = abspath(args.output_json)

    main(args.dataset_dir, args.output_json)
