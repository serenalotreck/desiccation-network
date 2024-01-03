"""
Spot checks for  wos_pull_papers.py

Author: Serena G. Lotreck
"""
import pytest
from lxml import etree
import sys

sys.path.append('../citation_network/')
import wos_pull_papers as wpp

######################## update_refs_with_abstracts ############################


@pytest.fixture
def original_search():
    return [
        {
            'UID':
            'paper1',
            'year':
            2021,
            'title':
            'This is paper 1',
            'abstract':
            'Paper 1 is about X',
            'references': [
                {
                    'UID': 'ref1',
                    'title': 'This is ref 1',
                    'year': 2005
                },
                {
                    'UID': 'paper2',
                    'title': 'This is paper 2',
                    'year': 2022
                },
                {
                    'title': 'Random paper',
                    'year': 1967
                }  # Should get dropped
            ]
        },
        {
            'UID':
            'paper2',
            'year':
            2022,
            'title':
            'This is paper 2',
            'abstract':
            'Paper 2 is about Y',
            'references': [
                {
                    'UID': 'ref2',
                    'title':
                    'This is ref 2',  # Won't have an abstract, should get dropped
                    'year': 2007
                },
                {
                    'UID': 'paper2',
                    'title': 'This is paper 2'  # Should get a year
                }
            ]
        },
        {
            'UID':
            'paper3',
            'year':
            2023,
            'title':
            'This is paper 3',
            'abstract':
            'Paper 3 is about Z',
            'references': [
                {
                    'UID': 'ref3',
                    'title': 'This is ref 3',
                    'year': 2000
                },
                {
                    'title': 'This is ref 4',
                    'year': 2004  # Should get dropped for no UID
                },
                {
                    'UID': 'ref5',
                    'title': 'This is ref 5',
                    'year': 2005
                },
                {
                    'UID': 'ref6',
                    'title': 'This is ref 6',
                    'year': 2006
                },
                {
                    'UID': 'ref7',
                    'title':
                    'This is ref 7'  # Should still get kept with no year
                }
            ]
        },
        {
            'UID': 'paper4',
            'year': 1997,
            'title': 'This is paper 4',
            'references': []  # Should show up the same in the new version
        }
    ]


@pytest.fixture
def all_paper_jsonl():
    return [
        {
            'UID': 'ref1',
            'title': 'This is ref 1',
            'year': 2005,
            'abstract': 'Reference 1 is about A'
        },
        {
            'UID': 'paper2',
            'title': 'This is paper 2',
            'year': 2022,
            'abstract': 'Paper 2 is about Y'
        },
        {
            'UID': 'ref2',
            'title':
            'This is ref 2',  # Won't have an abstract, should get dropped
            'year': 2007
        },
        {
            'UID': 'ref3',
            'title': 'This is ref 3',
            'year': 2000,
            'abstract': 'Reference 3 is about C'
        },
        {
            'UID': 'ref5',
            'title': 'This is ref 5',
            'year': 2005,
            'abstract': 'Reference 5 is about E'
        },
        {
            'UID': 'ref6',
            'title': 'This is ref 6',
            'year': 2006,
            'abstract': 'Reference 6 is about F'
        },
        {
            'UID': 'ref7',
            'title': 'This is ref 7',
            'abstract': 'Reference 7 is about G'
        }
    ]


@pytest.fixture
def updated_all_paper_jsonl():
    return [
        {
            'UID':
            'paper1',
            'year':
            2021,
            'title':
            'This is paper 1',
            'abstract':
            'Paper 1 is about X',
            'references': [{
                'UID': 'ref1',
                'title': 'This is ref 1',
                'year': 2005,
                'abstract': 'Reference 1 is about A'
            }, {
                'UID': 'paper2',
                'title': 'This is paper 2',
                'year': 2022,
                'abstract': 'Paper 2 is about Y'
            }]
        },
        {
            'UID':
            'paper2',
            'year':
            2022,
            'title':
            'This is paper 2',
            'abstract':
            'Paper 2 is about Y',
            'references': [{
                'UID': 'paper2',
                'title': 'This is paper 2',  # Should get a year
                'year': 2022,
                'abstract': 'Paper 2 is about Y'
            }]
        },
        {
            'UID':
            'paper3',
            'year':
            2023,
            'title':
            'This is paper 3',
            'abstract':
            'Paper 3 is about Z',
            'references': [
                {
                    'UID': 'ref3',
                    'title': 'This is ref 3',
                    'year': 2000,
                    'abstract': 'Reference 3 is about C'
                },
                {
                    'UID': 'ref5',
                    'title': 'This is ref 5',
                    'year': 2005,
                    'abstract': 'Reference 5 is about E'
                },
                {
                    'UID': 'ref6',
                    'title': 'This is ref 6',
                    'year': 2006,
                    'abstract': 'Reference 6 is about F'
                },
                {
                    'UID': 'ref7',
                    'title':
                    'This is ref 7',  # Should still get kept with no year
                    'abstract': 'Reference 7 is about G'
                }
            ]
        },
        {
            'UID': 'paper4',
            'year': 1997,
            'title': 'This is paper 4',
            'references': []  # Should show up the same in the new version
        }
    ]


def test_update_refs_with_abstracts(original_search, all_paper_jsonl,
                                    updated_all_paper_jsonl):

    result = wpp.update_refs_with_abstracts(all_paper_jsonl, original_search)

    assert result == updated_all_paper_jsonl


############################# convert_xml_reference ############################


@pytest.fixture
def single_reference_tree():
    xml_string = '<reference xmlns="http://clarivate.com/schema/wok5.30/public/FullRecord" occurenceOrder="3">\n<uid>WOS:000288170900008</uid>\n<citedAuthor>Barney, JN</citedAuthor>\n<year>2011</year>\n<page>ARTN e17222</page>\n<volume>6</volume>\n<citedTitle>Global Climate Niche Estimates for Bioenergy Crops and Invasive Species of Agronomic Origin: Potential Problems and Opportunities</citedTitle>\n<citedWork>PLOS ONE</citedWork>\n<doi>10.1371/journal.pone.0017222</doi>\n</reference>\n\n'
    return etree.fromstring(xml_string)


@pytest.fixture
def single_ref_result():
    return {
        'UID':
        'WOS:000288170900008',
        'year':
        '2011',
        'title':
        'Global Climate Niche Estimates for Bioenergy Crops and Invasive Species of Agronomic Origin: Potential Problems and Opportunities'
    }


def test_convert_xml_reference(single_reference_tree, single_ref_result):

    result = wpp.convert_xml_reference(single_reference_tree)

    assert result == single_ref_result


################################## convert_xml_paper ###########################


@pytest.fixture
def paper_tree():
    tree = etree.parse('SampleXML.xml')
    for record in tree.getroot():
        return etree.ElementTree(record)


@pytest.fixture
def paper_json_with_refs():
    return {
        'UID':
        'WOS:000623021900024',
        'title':
        'COMPARISON OF SPRING AND SUMMER SOWING OF SUGAR BEET GENOTYPES AT DIFFERENT HARVEST DATES TO SHIFT FROM TRADITIONAL CROP TO CASH CROP IN CENTRAL IRAN',
        'abstract':
        "This study was carried out in Karaj, Iran in 2017 and 2018 to assess the efficacy of summer sowing (June 22) versus spring sowing (April 20) of six sugar beet genotypes at three harvest times (October 13, November 2, and November 23) via the measurement of catalase (CAT), malondialdehyde (MDA), and agronomic traits. Results showed that in both sowing dates, higher growth and temperature were related to higher CAT activity and MDA content, and the maximum MDA and CAT activity were observed in 1700-1900 growth degree days (GDD). Genotypes responded to the shortening of the growth period differently. The best genotypes for summer sowing were found to be 'Paya', 'IR7', and 'Pars' when a combination of the least response to delayed sowing and the highest root yield in the summer sowing conditions was considered. Compared to the spring sowing, the summer sowing decreased white sugar yield (WSY) of all cultivars by 28.3-50.5% in the first year and 5.3-32.4% in the second year. 'Paya' and 'IR7' were the most capable cultivars in preserving WSY so that they maintained 70% of their yields. In addition, the genotypes exhibited their highest WSY at the November 23 harvest date so that root, raw sugar and white sugar yields were 41.21, 6.35 and 5.02 t ha(-1) higher at the November 23 harvest date than at the October 13 harvest date, respectively. Based on the results, if summer-sown sugar beets are considered as a cash crop in rotation with grains and there is no limitation on water supply, it can then be recommended to farmers as it can make good profits for them.",
        'year':
        '2021',
        'paper_keywords': [
            'CAT', 'MDA', 'root yield', 'sugar yield', 'WUE'
            ],
        'references': [{
            'UID': 'WOS:000288170900008',
            'title':
            'Global Climate Niche Estimates for Bioenergy Crops and Invasive Species of Agronomic Origin: Potential Problems and Opportunities',
            'year': '2011'
        }, {
            'UID': 'WOS:000466609800008',
            'title':
            'Water deficit stress, ROS involvement, and plant performance',
            'year': '2019'
        }, {
            'UID': 'WOS:000261724800002',
            'title':
            'Impact of different environments in Europe on yield and quality of sugar beet genotypes',
            'year': '2009'
        }, {
            'UID': 'WOS:000273166600022',
            'title':
            'Evaluation of the influence of irrigation methods and water quality on sugar beet yield and water use efficiency',
            'year': '2010'
        }, {
            'UID': 'WOS:000371553500005',
            'title':
            'Histone acetylation influences the transcriptional activation of POX in Beta vulgaris L. and Beta maritima L. under salt stress',
            'year': '2016'
        }, {
            'UID': 'WOS:000418236000001',
            'title':
            'Plant adaptations to the combination of drought and high temperatures',
            'year': '2018'
        }],
        'dynamic_keys': ['Chemistry', 'Membrane Science', 'Sugar Beet'],
        'static_keys': ['Agriculture, Multidisciplinary', 'Agriculture']
    }


@pytest.fixture
def paper_json_as_reference():
    return {
        'UID': 'WOS:000623021900024',
        'title':
        'COMPARISON OF SPRING AND SUMMER SOWING OF SUGAR BEET GENOTYPES AT DIFFERENT HARVEST DATES TO SHIFT FROM TRADITIONAL CROP TO CASH CROP IN CENTRAL IRAN',
        'abstract':
        "This study was carried out in Karaj, Iran in 2017 and 2018 to assess the efficacy of summer sowing (June 22) versus spring sowing (April 20) of six sugar beet genotypes at three harvest times (October 13, November 2, and November 23) via the measurement of catalase (CAT), malondialdehyde (MDA), and agronomic traits. Results showed that in both sowing dates, higher growth and temperature were related to higher CAT activity and MDA content, and the maximum MDA and CAT activity were observed in 1700-1900 growth degree days (GDD). Genotypes responded to the shortening of the growth period differently. The best genotypes for summer sowing were found to be 'Paya', 'IR7', and 'Pars' when a combination of the least response to delayed sowing and the highest root yield in the summer sowing conditions was considered. Compared to the spring sowing, the summer sowing decreased white sugar yield (WSY) of all cultivars by 28.3-50.5% in the first year and 5.3-32.4% in the second year. 'Paya' and 'IR7' were the most capable cultivars in preserving WSY so that they maintained 70% of their yields. In addition, the genotypes exhibited their highest WSY at the November 23 harvest date so that root, raw sugar and white sugar yields were 41.21, 6.35 and 5.02 t ha(-1) higher at the November 23 harvest date than at the October 13 harvest date, respectively. Based on the results, if summer-sown sugar beets are considered as a cash crop in rotation with grains and there is no limitation on water supply, it can then be recommended to farmers as it can make good profits for them.",
        'year': '2021',
        'dynamic_keys': ['Chemistry', 'Membrane Science', 'Sugar Beet'],
        'static_keys': ['Agriculture, Multidisciplinary', 'Agriculture'],
        'paper_keywords': [
            'CAT', 'MDA', 'root yield', 'sugar yield', 'WUE'
            ]
    }


def test_convert_xml_paper_kind_full(paper_tree, paper_json_with_refs):

    result = wpp.convert_xml_paper(paper_tree, kind='full')

    assert result == paper_json_with_refs


def test_convert_paper_xml_kind_ref_only(paper_tree, paper_json_as_reference):

    result = wpp.convert_xml_paper(paper_tree, kind='ref_only')

    assert result == paper_json_as_reference
