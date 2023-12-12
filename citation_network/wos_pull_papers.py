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


def convert_xml_paper(paper):
    """
    Convert a single paper from WoS XML to json.

    parameters:
        paper, ElementTree: child of XML dataset to convert

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
            # References
            refs_list = []
            for refs in fullrec.findall('{http://clarivate.com/schema/wok5.30/public/FullRecord}references'):
                for ref in refs:
                    refs_list.append(convert_xml_reference(etree.ElementTree(ref)))
            paper_json['references'] = refs_list
            # Abstract
            for abstr in fullrec.findall('{http://clarivate.com/schema/wok5.30/public/FullRecord}abstract'):
                paper_json['abstract'] = abstr.text
        # Keywords
        static_keys = []
        for fullrec in static.findall('{http://clarivate.com/schema/wok5.30/public/FullRecord}fullrecord_metadata'):
            for category in fullrec.findall('{http://clarivate.com/schema/wok5.30/public/FullRecord}category_info'):
                for subjects in category.findall('{http://clarivate.com/schema/wok5.30/public/FullRecord}subjects'):
                    for subj in subjects:
                        static_keys.append(subj.text)
        paper_json['static_keywords'] = static_keys
        # Dynamic subjects
        ## TODO come back for this
#         dynamic_keys = []
#         for dynamo in paper.findall('{http://clarivate.com/schema/wok5.30/public/FullRecord}dynamic_data'):
#             for cluster in dynamo.findall('{http://clarivate.com/schema/wok5.30/public/FullRecord}cluster_related'):
#                 pass

    return paper_json


def filter_xml_papers(xml, uids_to_keep):
    """
    Filter an XML dataset to include only papers from a given list and convert
    to jsonl. Also filters out non-English language papers.

    parameters:
        xml, ElementTree: dataset to parse
        uids_to_keep, list of str: UIDs to keep

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
            paper_dict = convert_xml_paper(etree.ElementTree(record))
            paper_jsonl.append(paper_dict)

    return paper_jsonl

def main(xml_dir, gui_search, output_jsonl):

    # Read in the files we want and get UID list
    print('\nReading in search results...')
    search_res = pd.read_csv(gui_search, sep='\t')
    uids_to_keep = search_res['UT'].values.tolist()
    years_to_search = list(search_res['PY'].dropna().astype(int).unique())
    print(years_to_search)
    print(f'There are {len(uids_to_keep)} papers in the search results. There '
            f'are {len(years_to_search)} years to examine to find these results.')

    # Read in the XMLs
    print('\nReading in XML data and processing...')
    to_read = []
    for f in listdir(xml_dir):
        if isfile(f'{xml_dir}/{f}') and splitext(f)[1] == '.xml':
            year = int(f.split('_')[1])
            if year in years_to_search:
                to_read.append(f)
    print(f'After filtering years, there are {len(to_read)} XML files to parse.')
    all_paper_jsonl = []
    for f in tqdm(to_read):
        print(f'\nChecking XML wtih filename {f}:')
        tree = etree.parse(f'{xml_dir}/{f}')
        set_papers = filter_xml_papers(tree, uids_to_keep)
        all_paper_jsonl.extend(set_papers)
        del tree
    print(f'{len(all_paper_jsonl)} papers of the requested {len(uids_to_keep)} '
            'were recovered')

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
    parser.add_argument('gui_search', type=str,
            help='Path to the combined fast 5000 outputs from a WoS search, '
                'extension is .csv')
    parser.add_argument('output_jsonl', type=str,
            help='Path to save output, extension is .jsonl')


    args = parser.parse_args()

    args.xml_dir = abspath(args.xml_dir)
    args.gui_search = abspath(args.gui_search)
    args.output_jsonl = abspath(args.output_jsonl)

    main(args.xml_dir, args.gui_search, args.output_jsonl)

