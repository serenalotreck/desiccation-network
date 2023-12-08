"""
Script to get papers from the XML dataset.

Author: Serena G. Lotreck
"""
import argparse
from os.path import abspath, isfile, splitext
from os import listdir
from tqdm import tqdm
import xml.etree.ElementTree as ET
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
        # References
        refs_list = []
        for fullrec in static.findall('{http://clarivate.com/schema/wok5.30/public/FullRecord}fullrecord_metadata'):
            for refs in fullrec.findall('{http://clarivate.com/schema/wok5.30/public/FullRecord}references'):
                for ref in refs:
                    refs_list.append(convert_xml_reference(ET.ElementTree(ref)))
        paper_json['references'] = refs_list
        # Keywords
        static_keys = []
        for fullrec in static.findall('{http://clarivate.com/schema/wok5.30/public/FullRecord}fullrecord_metadata'):
            for category in fullrec.findall('{http://clarivate.com/schema/wok5.30/public/FullRecord}category_info'):
                for subjects in category.findall('{http://clarivate.com/schema/wok5.30/public/FullRecord}subjects'):
                    for subj in subjects:
                        static_keys.extend(subj.text.split())
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
                in_uids = True
        # Check if the paper is in English
        for static in record.findall('{http://clarivate.com/schema/wok5.30/public/FullRecord}static_data'):
            for fullrec in static.findall('{http://clarivate.com/schema/wok5.30/public/FullRecord}fullrecord_metadata'):
                for langs in fullrec.findall('{http://clarivate.com/schema/wok5.30/public/FullRecord}normalized_languages'):
                    for lang in langs:
                        if lang.text == 'English':
                            in_english = True
        # Format
        if in_uids and in_english:
            paper_dict = convert_xml_paper(ET.ElementTree(record))
            paper_jsonl.append(paper_dict)

    return paper_jsonl

def main(xml_dir, gui_search, output_jsonl):

    # Read in the XMLs
    print('\nReading in all XML data...')
    xmls = []
    for f in tqdm(listdir(xml_dir)):
        if isfile(f) and splitext(f)[1] == '.xml':
            tree = ET.parse(f{xml_dir}/{f})
            xmls.append(tree)

    # Read in the files we want and get UID list
    print('\nReading in search results...')
    search_res = pd.read_csv(gui_search, sep='\t')
    uids_to_keep = search_res['UT'].values.tolist()
    print(f'There are {len(uids_to_keep)} papers in the search results')

    # Do the search
    print('\nLooking for papers...')
    all_paper_jsonl = []
    for docset in tqdm(xmls):
        set_papers = filter_xml_papers(docset, uids_to_keep)
        all_paper_jsonl.extend(set_papers)

    # Save
    print('\nSaving...')
    with jsonlines.open(output_jsonl) as writer:
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

