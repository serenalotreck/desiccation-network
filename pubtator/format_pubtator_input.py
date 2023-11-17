"""
Format Semantic Scholar search output for input to PubTator.

Author: Serena G. Lotreck
"""
import argparse
from os.path import abspath
import jsonlines
from tqdm import tqdm
import json


def main(data_to_format, input_dir_loc):

    # Read in the data
    print('\nReading in data...')
    with jsonlines.open(data_to_format) as reader:
        papers = []
        for obj in reader:
            papers.append(obj)

    # Determine if nested or not; if nested, flatten
    print('\nChecking if the data is nested...')
    try:
        flat_papers = {}
        for p in papers:
             flat_papers[p['paperId']] = p
             for r in p['references']:
                 flat_papers[r['paperId']] = r
        print('Data is nested!')
    except KeyError:
        flat_papers = {p['paperId']: p for p in papers}
        print('Data is not nested!')

    # Format as json
    print('\nFormatting papers as json...')
    pubtator_papers = {}
    nonepapers = 0
    for pid, p in tqdm(flat_papers.items()):
        if pid is not None:
            try:
                if p['abstract'] is not None:
                    paper_text = p['title'] + p['abstract']
                else:
                    paper_text = 'TITLE_ONLY ' + p['title']
            except KeyError:
                paper_text = 'TITLE_ONLY ' + p['title']
            doc_json = {'sourcedb': 'user',
                    'sourceid': pid,
                    'text': paper_text}
            pubtator_papers[pid] = doc_json
        else:
            nonepapers += 1
    print(f'{nonepapers} papers were dropped because their  paperId was None')

    # Save
    print('\nSaving papers...')
    for pid, paper_json in tqdm(pubtator_papers.items()):
        with open(f'{input_dir_loc}/{pid}.json', 'w') as myf:
            json.dump(paper_json, myf)

    print('\nDone!')


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Format PubTator input')

    parser.add_argument('data_to_format', type=str,
            help='Path to .jsonl dataset to format. Can be flattened or have '
            'nested references.')
    parser.add_argument('input_dir_loc', type=str,
            help='Path to PubTator input directory to save files.')


    args = parser.parse_args()

    args.data_to_format = abspath(args.data_to_format)
    args.input_dir_loc = abspath(args.input_dir_loc)

    main(args.data_to_format, args.input_dir_loc)
