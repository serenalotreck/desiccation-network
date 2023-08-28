"""
Code to pull papers and their references for a given search result.

Uses the Semantic Scholar Academic Graph API.

Obtains abstracts for initial search results on the first pass, then pulls the
abstracts for each reference, and combines into one output.

Limitations: Can only pull the first 10,000 papers for a query. Is slow.

Author: Serena G. Lotreck
"""
import argparse
from os.path import abspath
import requests
from tqdm import tqdm
from collections import defaultdict
import sys

sys.path.append('../data/')
from semantic_scholar_API_key import API_KEY

header = {'x-api-key': API_KEY}
import json
import jsonlines


def main(search_term, out_path, saved_jsonl, intermediate_path):

    # Make initial search
    print('\nMaking initial search query...')
    if saved_jsonl != '':
        with jsonlines.open(saved_jsonl) as reader:
            search_results = []
            for obj in reader:
                search_results.append(obj)
        print(f'Read in initial search results form {saved_jsonl}')
    else:
        search_results = []
        for offset in tqdm(range(0, 10000, 100)):
            query = f'http://api.semanticscholar.org/graph/v1/paper/search?query=desiccation+tolerance&offset={offset}&limit=99&fields=title,abstract,references'
            search = requests.get(query, headers=header).json()
            search_results.append(search)
        if intermediate_path != '':
            init_result_path = f'{intermediate_path}_initial_results.jsonl'
            with jsonlines.open(init_result_path, 'w') as writer:
                writer.write_all(search_results)
            print(f'Saved initial search results to {init_result_path}')
    search_results = [p for search in search_results for p in search['data']]
    print(
        f'There are {len(search_results)} papers in the initial search results.'
    )

    # Get abstracts for references
    print('\nMaking reference abstract search query...')
    ref_dict = {}
    for paper in tqdm(search_results):
        for ref in paper['references']:
            query = f'http://api.semanticscholar.org/graph/v1/paper/{ref["paperId"]}?fields=title,abstract'
            search = requests.get(query, headers=header).json()
            ref_dict[paper["paperId"]] = search
    print(f'There are {len(ref_dict)} references in this dataset.')
    if intermediate_path != '':
        ref_path = f'{intermediate_path}_reference_abstracts.json'
        with open(ref_path, 'w') as myf:
            json.dump(myf, ref_dict)
        print(f'Saved reference abstracts to {ref_path}')

    # Combine into one output dict
    print('\nCombining all results...')
    for initial_paper in tqdm(search_results['data']):
        for ref_paper in initial_paper['references']:
            ref_paper['abstract'] = ref_dict[ref_paper['paperId']]

    # Save
    print('\nSaving results...')
    with open(out_path, 'w') as myf:
        jsonl.dump(myf, search_results)
    print(f'Saved output as {out_path}')

    print('\nDone!')


if __name__ == "__main__":

    parser = argparse.ArgumentParser(description='Get citation network papers')

    parser.add_argument('search_term',
                        type=str,
                        help='Term to search. Replace spaces with +.')
    parser.add_argument('out_path',
                        type=str,
                        help='File name with full path to save output. '
                        'Extension is .json')
    parser.add_argument('-saved_jsonl', type=str, default='',
                        help='Path to a jsonl of saved search results that '
                        'have not been combined or had abstracts pulled for '
                        'references. Can be used to start process at '
                        'intermediate stage')
    parser.add_argument('-intermediate_path', type=str,
                        help='Path with file name but no extension. If passed,'
                        'save intermediate results with this path.')

    args = parser.parse_args()

    args.out_path = abspath(args.out_path)
    if args.saved_jsonl != '':
        args.saved_jsonl = abspath(args.saved_jsonl)
    if args.intermediate_path != '':
        args.intermediate_path = abspath(args.intermediate_path)

    main(args.search_term, args.out_path, args.saved_jsonl,
            args.intermediate_path)
