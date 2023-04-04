"""
Build a traditional directed citation network.

Author: Serena G. Lotreck
"""
import argparse
from os.path import abspath
from tethne.readers import wos
from tethne.networks.papers import direct_citation
from tethne.writers.graph import to_graphml
from taxonerd import TaxoNERD


def classify_paper(paper, nlp):
    """
    Get the study organism kingdom from a paper.

    parameters:
        paper, tethne.classes.paper.Paper object: paper to check
        nlp, spacy NLP object: TaxoNERD spacy pipeline

    returns:
        king, str: 'Animal', 'Plant' or 'Microbe' if paper contains at least
        one of title or abstract, otherwise returns None
    """
    # Get title
    try:
        title = paper['title']
    except AttributeError:
        title = ''

    # Get abstract
    try:
        abstract = paper['abstract']
    except AttributeError:
        abstarct = ''

    # If one is missing, operate only on the other, if both gone, ignore
    if title == '' and abstract != '':
        pass
    elif (title != '' and abstract == ''):
        pass
    elif title == '' and abstract == '':
        return None
    else:
        # Do the thing
        pass


def classify_nodes(papers, nlp, out_loc, out_prefix):
    """
    Find the kingdom (plant, animal, microbe) of the study organism of each
    paper. Follows this general algorithm:

        1. Use taxoNERD to extract species names from title and abstract
        2. Use NCBITaxon to classify each species name into a kingdom
        3. If there are classifications in both the title and the abstract,
        compare the kingdoms extracted from title and abstract:
            a. If they're the same (expected), this is the study organism
            kingdom
            b. If they're different, use the kingdom in the title
        4. If there's no classification in the abstract or title but there is
        in the other:
            a. If there's only one kingdom classification, use it as the study
            organism
        5. Catch all instances that fall through this algorithm without being
        classified and save to a file

    paramters:
        papers, tethne.classes.Corpus object: papers to classify
        nlp, spacy NLP object: TaxoNERD spacy pipeline
        out_loc, str: directory to save output
        out_prefix, str: string to prepend to output files

    returns:
        TODO decide what output format is best
    """
    for paper in papers:

        # Get kingdom
            king = classify_paper(paper, nlp)

            if king is None:
                # Do something to save to missed outputs
                pass
            else:
                # Do something to put in what gets returned
                pass



def main(wos_file, out_loc, out_prefix):

    # Read in the WOS file
    papers = wos.read(wos_file)

    # Classify the nodes by study system
    taxonerd = TaxoNERD(prefer_gpu=True)
    nlp = taxonerd.load(model="en_core_eco_biobert", linker="ncbi_taxonomy", threshold=0.7)
    classed_papers = classify_nodes(papers, nlp)

    # Build the network
    graph = direct_citation(papers)

    # Output in file renderable by cytoscape
    out_file = f'{out_loc}/{out_prefix}_citation_network.graphml'
    to_graphml(graph, out_file)

if __name__ == "__main__":

    parser = argparse.ArgumentParser(description='Build citation network')

    parser.add_argument('wos_file', type=str,
            help='Path to Web of Science Full Citation output')
    parser.add_argument('out_loc', type=str,
            help='Path to directory to save output')
    parser.add_argument('out_prefix', type=str,
            help='String to prepend to output file name')
    parser.add_argument('-v', '--verbose', action='store_true',
            help='Whether or not to print updates')

    args = parser.parse_args()

    args.wos_file = abspath(args.wos_file)
    args.out_loc = abspath(args.out_loc)

    verboseprint = print if args.verbose else lambda *a, **k: None

    main(args.wos_file, args.out_loc, args.out_prefix)
