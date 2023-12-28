"""
Script to get papers from the XML dataset.

Author: Serena G. Lotreck
"""
import argparse
from os.path import abspath, isfile, splitext
from os import listdir
from tqdm import tqdm
from lxml import etree
import pandas as pd
import jsonlines
import json
from multiprocessing import Pool, cpu_count
from math import ceil
import time


def update_refs_with_abstracts(all_paper_jsonl, original_search):
    """
    Adds abstracts to references in original search results.

    parameters:
        all_paper_jsonl, list of dict: result of XML filtering on reference UIDs
        original_search, list of dict: jsonl from first round search

    returns:
        updated_all_paper_jsonl, list of dict: results with reference abstracts
    """
    # Index by UID
    results = {p['UID']: p for p in all_paper_jsonl}
    # Build updated paper elements
    updated_all_paper_jsonl = []
    for p in original_search:
        full_paper_json = {}
        for name, elt in p.items():
            # Put all original elements back
            if name != 'references':
                full_paper_json[name] = elt
            # Update the references with abstracts
            else:
                updated_refs = []
                for r in p['references']:
                    uid_of_ref = r['UID']
                    try:
                        r['abstract'] = results[uid_of_ref]['abstract']
                    except KeyError:
                        print(f'No abstract found for reference {uid_of_ref}')
                    # Check if we put back a year, if not, add one
                    if 'year' not in r.keys():
                        try:
                            r['year'] = results[uid_of_ref]['year']
                        except KeyError:
                            print(f'No year found for paper {uid_of_ref}.')
                    updated_refs.append(r)
                full_paper_json['references'] = updated_refs
        updated_all_paper_jsonl.append(full_paper_json)

    return updated_all_paper_jsonl


def convert_xml_reference(ref):
    """
    Convert a reference.

    parameters:
        ref, ElementTree: reference to convert

    returns:
        ref_json, dict: formatted ref
    """
    ref_json = {}

    # UID
    for uid in ref.findall('{http://clarivate.com/schema/wok5.30/public/FullRecord}uid'):
        ref_json['UID'] = uid.text
    # Year
    for year in ref.findall('{http://clarivate.com/schema/wok5.30/public/FullRecord}year'):
        ref_json['year'] = year.text
    # Title
    for title in ref.findall('{http://clarivate.com/schema/wok5.30/public/FullRecord}citedTitle'):
        ref_json['title'] = title.text

    return ref_json


def convert_xml_paper(paper, kind):
    """
    Convert a single paper from WoS XML to json.

    parameters:
        paper, ElementTree: child of XML dataset to convert
        kind, str: "full" or "ref_only"

    returns:
        paper_json, dict: paper in json format
    """
    paper_json = {}

    # UID
    for uid in paper.findall('{http://clarivate.com/schema/wok5.30/public/FullRecord}UID'):
        paper_json['UID'] = uid.text
        print(f'Converting paper {uid.text}...')
    for static in paper.findall('{http://clarivate.com/schema/wok5.30/public/FullRecord}static_data'):
        for summary in static.findall('{http://clarivate.com/schema/wok5.30/public/FullRecord}summary'):
            # Title
            for titles in summary.findall('{http://clarivate.com/schema/wok5.30/public/FullRecord}titles'):
                for title in titles:
                    if title.attrib['type'] == 'item':
                        paper_json['title'] = title.text
            # Year
            for pub_info in summary.findall('{http://clarivate.com/schema/wok5.30/public/FullRecord}pub_info'):
                paper_json['year'] = pub_info.attrib['pubyear']
        for fullrec in static.findall('{http://clarivate.com/schema/wok5.30/public/FullRecord}fullrecord_metadata'):
            if kind == "full":
                # References
                refs_list = []
                for refs in fullrec.findall('{http://clarivate.com/schema/wok5.30/public/FullRecord}references'):
                    for ref in refs:
                        refs_list.append(convert_xml_reference(etree.ElementTree(ref)))
                paper_json['references'] = refs_list
            # Abstract
            for abstracts in fullrec.findall('{http://clarivate.com/schema/wok5.30/public/FullRecord}abstracts'):
                abstract_list = []
                for abstr in abstracts:
                    for ab in abstr:
                        for a in ab:
                            abstract_list.append(a.text)
                if len(abstract_list) > 1:
                    print(f'There are {len(abstract_list)} abstracts for this paper:')
                    print("\n\n".join(abstract_list))
                paper_json['abstract'] = ' '.join(abstract_list)
        # Keywords
        static_keys = []
        for fullrec in static.findall('{http://clarivate.com/schema/wok5.30/public/FullRecord}fullrecord_metadata'):
            for category in fullrec.findall('{http://clarivate.com/schema/wok5.30/public/FullRecord}category_info'):
                for subjects in category.findall('{http://clarivate.com/schema/wok5.30/public/FullRecord}subjects'):
                    for subj in subjects:
                        static_keys.append(subj.text)
        paper_json['static_keywords'] = static_keys
        # Dynamic subjects
        dynamic_keys = []
        for dynamo in paper.findall('{http://clarivate.com/schema/wok5.30/public/FullRecord}dynamic_data'):
            for cr in dynamo.findall('{http://clarivate.com/schema/wok5.30/public/FullRecord}citation_related'):
                for ct in cr.findall('{http://clarivate.com/schema/wok5.30/public/FullRecord}citation_topics'):
                    for subj_group in ct.findall('{http://clarivate.com/schema/wok5.30/public/FullRecord}subj-group'):
                        for subj in subj_group.findall('{http://clarivate.com/schema/wok5.30/public/FullRecord}subject'):
                            dynamic_keys.append(subj.text)
        paper_json['dynamic_keys'] = dynamic_keys

    return paper_json


def filter_xml_papers(xml, uids_to_keep, kind):
    """
    Filter an XML dataset to include only papers from a given list and convert
    to jsonl. Also filters out non-English language papers.

    parameters:
        xml, ElementTree: dataset to parse
        uids_to_keep, list of str: UIDs to keep
        kind, str: "full" or "ref_only"

    returns:
        paper_jsonl, list of dict: papers to keep in jsonl format
    """
    paper_jsonl = []

    for record in xml.getroot():
        in_uids = False
        in_english = False
        # Check the UID
        for uid in record.findall('{http://clarivate.com/schema/wok5.30/public/FullRecord}UID'):
            if uid.text in uids_to_keep:
                print('Found a paper to keep!')
                in_uids = True
        # Check if the paper is in English
        for static in record.findall('{http://clarivate.com/schema/wok5.30/public/FullRecord}static_data'):
            for fullrec in static.findall('{http://clarivate.com/schema/wok5.30/public/FullRecord}fullrecord_metadata'):
                for langs in fullrec.findall('{http://clarivate.com/schema/wok5.30/public/FullRecord}normalized_languages'):
                    for lang in langs:
                        if lang.text == 'English':
                            in_english = True

        # Format
        if in_uids:
            print(f'Is it also an English paper?: {in_english}')
        if in_uids and in_english:
            paper_dict = convert_xml_paper(etree.ElementTree(record), kind)
            paper_jsonl.append(paper_dict)

    return paper_jsonl


def read_and_process_xml(xml_dir, uids_to_keep, to_read, kind):
    """
    Reads in XML files one at a time and processes them before purging them from
    memory.

    parameters:
        xml_dir, str: path to XML files
        uids_to_keep, list of str: UIDs to search for
        to_read, list of str: file paths of XML files to read
        kind, str: "full" or "ref_only"

    returns:
        all_paper_jsonl, list of dict: updated/formated papers
    """
    all_paper_jsonl = []
    found = {uid: False for uid in uids_to_keep}
    for f in tqdm(to_read):
        print(f'\nChecking XML with filename {f}:')
        tree = etree.parse(f'{xml_dir}/{f}')
        set_papers = filter_xml_papers(tree, uids_to_keep, kind)
        all_paper_jsonl.extend(set_papers)
        del tree
        uids_found = [p['UID'] for p in set_papers]
        for uid in uids_found:
            found[uid] = True
        if all(value for value in found.values()):
            break

    return all_paper_jsonl


def narrow_search_files(xml_dir, uid_source, kind, uid_map):
    """
    Use provided information to narrow down the list of which XML files need to
    be read.

    parameters:
        xml_dir, str: directory with XML files
        uid_source, either pd df or list of dict: either search_res or
            original_search, depending on what kind is
        kinf, str: either "full" or "ref_only"
        uid_map, dict: keys are UIDs, values are XML filenames

    returns:
        to_read, list of str: list of files to read
        uids_to_keep, list of str: list of UIDs to look for
    """
    # Get the UIDs to keep and years if necessary
    if kind == 'full':
        uids_to_keep = uid_source['UT'].values.tolist()
        all_uid_set_len = len(set(uids_to_keep))
        uids_to_keep = list(set([uid for uid in uids_to_keep if uid[:4] == 'WOS:']))
        dropped_len = all_uid_set_len - len(uids_to_keep)
        print(f'{dropped_len} of {all_uid_set_len} were dropped because they were '
                'outside of the Core Collection.')
        if uid_map == '':
            print(uid_source['PY'].unique())
            years_to_search = list(uid_source['PY'].dropna().astype(int).unique())
            if len(uid_source['PY'].dropna()) != len(uid_source['PY']):
                filter_by_year = False
            else:
                filter_by_year = True
            print(years_to_search)
        print(f'There are {len(uids_to_keep)} papers in the search results.')
    else:
        uids_to_keep = []
        not_wos = 0
        total_refs = 0
        for p in uid_source:
            for r in p['references']:
                try:
                        uids_to_keep.append(r['UID'])
                except KeyError:
                    print(f'A reference for paper {p["UID"]} was dropped due to '
                        'missing UID.')
        all_uid_set_len = len(set(uids_to_keep))
        uids_to_keep = list(set([uid for uid in uids_to_keep if uid[:4] == 'WOS:']))
        dropped_len = all_uid_set_len - len(uids_to_keep)
        print(f'{dropped_len} of {all_uid_set_len} were dropped because their '
                'prefixes were outside of the Core Collection.')
        only_wos_set_len = len(uids_to_keep)
        uids_to_keep = list(set([uid for uid in uids_to_keep if len(uid.split('.')) == 1]))
        print(f'An additional {only_wos_set_len - len(uids_to_keep)} were '
                'dropped because their UIDs were derived from the citing paper '
                '(i.e. the reference is not in any WOS collection)')
        uids_to_keep = list(set(uids_to_keep))
        if uid_map == '':
            filter_by_year = True
            try:
                years_to_search = list(set([int(r['year']) for p in uid_source
                    for r in p['references']]))
            except KeyError:
                filter_by_year = False
                print('One or more references are missing a year, so all XMLs '
                    'must be searched.')
        print(f'There are {len(uids_to_keep)} unique references in the search results.')

    # Get the names of the files necessary to read to find all papers
    to_read = []
    if uid_map == '':
        if filter_by_year:
            for f in listdir(xml_dir):
                if isfile(f'{xml_dir}/{f}') and splitext(f)[1] == '.xml':
                    year = int(f.split('_')[1])
                    if year in years_to_search:
                        to_read.append(f)
            print(f'After filtering years, there are {len(to_read)} XML files to parse.')
        else:
            for f in listdir(xml_dir):
                if isfile(f'{xml_dir}/{f}') and splitext(f)[1] == '.xml':
                    to_read.append(f)
            print(f'Unable to filter by year, there are {len(to_read)} XML to parse.')
    else:
        print('\nReading in UID map...')
        with open(uid_map) as myf:
            uid_dict = json.load(myf)
        print('Choosing filenames to read...')
        suspiciously_missing = []
        for uid in tqdm(uids_to_keep):
            try:
                to_read.append(uid_dict[uid])
            except KeyError:
                suspiciously_missing.append(uid)
        print(f'There are {len(suspiciously_missing)} suspiciously missing UIDs')
        to_read = list(set(to_read))
        print(f'After filtering with the UID map, there are {len(to_read)} XML files to parse.')

    return to_read, uids_to_keep


def main(xml_dir, output_jsonl, gui_search, jsonl_to_modify, kind, uid_map,
        parallelize):

    # Read in the files we want and get UID list
    print('\nReading in search results...')
    if kind == 'full':
        search_res = pd.read_csv(gui_search, sep='\t')
        to_read, uids_to_keep = narrow_search_files(xml_dir, search_res, kind, uid_map)
    else:
        with jsonlines.open(jsonl_to_modify) as reader:
            original_search = []
            for obj in reader:
                original_search.append(obj)
        to_read, uids_to_keep = narrow_search_files(xml_dir, original_search, kind, uid_map)

    # Read in the XMLs
    print('\nReading in XML data and processing...')
    if parallelize:
        len_to_reads = (len(to_read)//cpu_count()) + 1
        to_reads = [to_read[i:i+len_to_reads] for i in range(0, len(to_read), len_to_reads)]
        with Pool(cpu_count()) as pool:
            result = pool.starmap(read_and_process_xml, [(xml_dir,
                uids_to_keep, this_read, kind) for this_read in to_reads])
            all_paper_jsonl = [paper for subset in result for
                    paper in subset]
        print(f'{len(all_paper_jsonl)} papers of the requested {len(uids_to_keep)} '
                'were recovered')
        if kind == 'ref_only':
            all_paper_jsonl = update_refs_with_abstracts(all_paper_jsonl, original_search)
    else:
        all_paper_jsonl = read_and_process_xml(xml_dir, uids_to_keep, to_read, kind)
        print(f'{len(all_paper_jsonl)} papers of the requested {len(uids_to_keep)} '
                'were recovered')
        if kind == 'ref_only':
            all_paper_jsonl = update_refs_with_abstracts(all_paper_jsonl, original_search)

    # Save
    print('\nSaving...')
    with jsonlines.open(output_jsonl, 'w') as writer:
        writer.write_all(all_paper_jsonl)
    print(f'Saved output as {output_jsonl}')

    print('\nDone!')


if __name__ == "__main__":

    parser = argparse.ArgumentParser(description='Get XML papers')

    parser.add_argument('xml_dir', type=str,
            help='Path to directory containing the annuals for all years')
    parser.add_argument('output_jsonl', type=str,
            help='Path to save output, extension is .jsonl')
    parser.add_argument('-uid_map', type=str, default='',
            help='Path to a json file with a list of the UIDs in each XML ')
    parser.add_argument('-gui_search', type=str, default='',
            help='Path to the combined fast 5000 outputs from a WoS search, '
                'extension is .csv')
    parser.add_argument('-jsonl_to_modify', type=str, default='',
            help='Jsonl from an initial XML pull, refence abstracts to be '
                'retrieved')
    parser.add_argument('--parallelize', action='store_true',
            help='Whether or not to retreive articles in parallel')

    args = parser.parse_args()

    args.xml_dir = abspath(args.xml_dir)
    args.output_jsonl = abspath(args.output_jsonl)

    assert not (args.gui_search == '' and args.jsonl_to_modify == ''), (
        'One of gui_search or jsonl_to_modify must be passed')

    if args.gui_search != '':
        assert args.jsonl_to_modify == '', (
            'Only one of gui_search and jsonl_to_modify can be passed')
        kind = 'full'
        args.gui_search = abspath(args.gui_search)
    elif args.jsonl_to_modify != '':
        assert args.gui_search == '', (
            'Only one of gui_search and jsonl_to_modify can be passed')
        kind = 'ref_only'
        args.jsonl_to_modify = abspath(args.jsonl_to_modify)

    if args.uid_map != '':
        args.uid_map = abspath(args.uid_map)

    if args.parallelize:
        print('\nParallelization has been requested. There are '
                f'{cpu_count()} available CPUs for this task.')

    start = time.time()
    main(args.xml_dir, args.output_jsonl, args.gui_search, args.jsonl_to_modify,
            kind, args.uid_map, args.parallelize)
    print(f'\n\n\nThe entire script took {time.time() - start} seconds to run.')
