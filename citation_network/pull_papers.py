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
from math import ceil

sys.path.append('../data/')
from semantic_scholar_API_key import API_KEY

header = {'x-api-key': API_KEY}
import json
import jsonlines


def main(search_term, out_path, relevance_search, total_results, batch_size, saved_jsonl,
        intermediate_path):

    # If provided, read in intermediate results
    if saved_jsonl != '':
        print('\nReading in provided search results...')
        with jsonlines.open(saved_jsonl) as reader:
            search_results = []
            for obj in reader:
                search_results.append(obj)
        print(f'Read in initial search results form {saved_jsonl}')

    # Make initial search
    else:
        print('\nMaking initial search query...')
        search_results = []
        for offset in tqdm(range(0, total_results, batch_size)):
            if relevance_search:
                if offset + batch_size == 1000:
                    query = f'http://api.semanticscholar.org/graph/v1/paper/search?query={search_term}&offset={offset}&limit={batch_size-1}&fields=title,abstract,references,year,s2FieldsOfStudy'
                else:
                    query = f'http://api.semanticscholar.org/graph/v1/paper/search?query={search_term}&offset={offset}&limit={batch_size}&fields=title,abstract,references,year,s2FieldsOfStudy'
            else:
                query = f'https://api.semanticscholar.org/graph/v1/paper/search/bulk/?query={search_term}&offset={offset}&limit={batch_size-1}&fields=title,abstract,references,year,s2FieldsOfStudy'
            succeeded = False
            reps = 0
            while not succeeded:
                search = requests.get(query, headers=header).json()
                try:
                    search['data']
                    succeeded = True
                except KeyError:
                    reps += 1
                    print(f'{reps} failed requests for offset number {offset}, repeating')
            search_results.append(search)

        # Save if requested
        if intermediate_path != '':
            print('\nsaving intermediate results...')
            init_result_path = f'{intermediate_path}_initial_results.jsonl'
            with jsonlines.open(init_result_path, 'w') as writer:
                writer.write_all(search_results)
            print(f'Saved initial search results to {init_result_path}')

    # Combine into one set of search results
    search_results = [p for search in search_results for p in search['data']]
    print(
        f'There are {len(search_results)} papers in the initial search results.'
    )

    # Get abstracts for references
    print('\nMaking reference abstract search query...')
    unique_ref_ids = list(set([r['paperId'] for p in search_results for r in
            p['references']]))
    ref_dict = {}
    lost_refs = 0
    if len(unique_ref_ids) > 500:
        top_num = int(ceil(len(unique_ref_ids) / 500.0)) * 500
        for i in tqdm(range(0, top_num, 500)):
            ids = unique_ref_ids[i: i+500]
            result = requests.post(
                    'https://api.semanticscholar.org/graph/v1/paper/batch',
                     params={'fields': 'title,abstract,year'},
                     json={'ids': ids}
                    ).json()
            for r in result:
                try:
                    ref_dict[r['paperId']] = r
                except TypeError:
                    lost_refs += 1
    else:
        result = requests.post(
                'https://api.semanticscholar.org/graph/v1/paper/batch',
                 params={'fields': 'title,abstract,year'},
                 json={'ids': unique_ref_ids}
                ).json()
        for r in result:
            try:
                ref_dict[r['paperId']] = r
            except TypeError:
                lost_refs += 1
    print(f'There are {len(unique_ref_ids)} unique references in this dataset. '
            f'{lost_refs} references were lost due to query failure.')

    # Save references if requested
    if intermediate_path != '':
        print('\nSaving intermediate references...')
        ref_path = f'{intermediate_path}_reference_abstracts.json'
        with open(ref_path, 'w') as myf:
            json.dump(ref_dict, myf)
        print(f'Saved reference abstracts to {ref_path}')

    # Combine into one output dict
    print('\nCombining all results...')
    lost_refs = 0
    for i, initial_paper in tqdm(enumerate(search_results)):
        for j, ref_paper in enumerate(initial_paper['references']):
            try:
                search_results[i]['references'][j] = ref_dict[ref_paper['paperId']]
            except KeyError:
                lost_refs += 1
    print(f'{lost_refs} additional references were lost due to missing paperId. '
            'These are mis-formatted citations that result in erroneous references.')

    # Save
    print('\nSaving final results...')
    with jsonlines.open(out_path, 'w') as writer:
        writer.write_all(search_results)
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
                        'Extension is .jsonl')
    parser.add_argument('--relevance_search', action='store_true',
                        help='Whether or not to use relevance search instead '
                        'of bulk seach. If passed, only 999 results will be '
                        'returned, instead of the 10000 default max.')
    parser.add_argument('-total_results', type=int, default=10000,
                        help='Number of search results to get, max is 10000, '
                        'default is 10000.')
    parser.add_argument('-batch_size', type=int, default=100,
                        help='Chunk size in which to retrieve docs, must be > 1 '
                        'and =< 100. Default is 100.')
    parser.add_argument('-saved_jsonl', type=str, default='',
                        help='Path to a jsonl of saved search results that '
                        'have not been combined or had abstracts pulled for '
                        'references. Can be used to start process at '
                        'intermediate stage')
    parser.add_argument('-intermediate_path', type=str, default='',
                        help='Path with file name but no extension. If passed,'
                        'save intermediate results with this path.')

    args = parser.parse_args()

    args.out_path = abspath(args.out_path)
    if args.saved_jsonl != '':
        args.saved_jsonl = abspath(args.saved_jsonl)
    if args.intermediate_path != '':
        args.intermediate_path = abspath(args.intermediate_path)

    if args.relevance_search:
        print('\nA relevance search has been requested, the provided request '
                f'of {args.total_results} results will be reduced to 9999.')
        args.total_results = 999

    main(args.search_term, args.out_path, args.relevance_search,
            args.total_results, args.batch_size, args.saved_jsonl,
            args.intermediate_path)
