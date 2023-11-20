"""
Formats the output of a PubTator annotation into a csv that can later be used
to build graphs.

Author: Serena G. Lotreck
"""
import argparse
from os.path import abspath, splitext
from os import listdir
import json
from tqdm import tqdm
import pandas as pd


def parse_doc(annotations_for_df, doc):
    """
    Get the text bound annotations for a document and add to the list for df
    formatting.

    parameters:
        annotations_for_df, dict of list: keys are paperId, ann_text, ann_type,
            db_grounding
        doc, dict: PubTator output for a single doc

    returns:
        annotations_for_df, dict: updated annotation dict
    """
    for ann in doc['denotations']:
        annotations_for_df['paperId'].append(doc['sourceid'])
        annotations_for_df['ann_type'].append(ann['obj'].split(':')[0])
        annotations_for_df['db_grounding'].append(ann['obj'].split(':')[1])
        ann_text = doc['text'][ann['span']['begin']:ann['span']['end']]
        annotations_for_df['ann_text'].append(ann_text)

    return annotations_for_df


def main(output_dir, csv_out_path):

    # Read in the output files
    print('\nReading in the files...')
    annotations = {}
    skipped = 0
    for f in listdir(output_dir):
        if splitext(f)[1] == '.json':
            try:
                with open(f'{output_dir}/{f}') as myf:
                    doc = json.load(myf)
                    annotations[splitext(f)[0]] = doc
            except json.decoder.JSONDecodeError:
                print(f'Document {f} is mis-formatted and is being skipped.')
                skipped += 1
    print(f'{skipped} of {len(listdir(output_dir))} documents were lost.')

    # Get the text for annotations and format for df
    print('\nFormatting annotations...')
    annotations_for_df = {'paperId': [], 'ann_text': [], 'ann_type': [],
            'db_grounding': []}
    for pid, doc in tqdm(annotations.items()):
        annotations_for_df = parse_doc(annotations_for_df, doc)

    # Make df
    print('\nMaking dataframe...')
    ann_df = pd.DataFrame.from_dict(annotations_for_df)
    print('Snapshot of the annotations df:')
    print(ann_df.head())

    # Save df
    print('\nSaving annotation df...')
    ann_df.to_csv(csv_out_path, index=False)

    print('\nDone!')


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Format PubTator output')

    parser.add_argument('output_dir', type=str,
            help='Path to folder containing output annotations.')
    parser.add_argument('csv_out_path', type=str,
            help='Path to save the output csv.')

    args = parser.parse_args()

    args.output_dir = abspath(args.output_dir)
    args.csv_out_path = abspath(args.csv_out_path)

    main(args.output_dir, args.csv_out_path)
