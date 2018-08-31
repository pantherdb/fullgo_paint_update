from xml.etree import ElementTree
from argparse import ArgumentParser

parser = ArgumentParser()
parser.add_argument("filepath")
args = parser.parse_args()

filepath = args.filepath
# tree = ElementTree.parse("resources/SEARCH_TYPE_AGG_FAMILY_ANNOTATION_INFO.txt")
tree = ElementTree.parse(filepath)
root = tree.getroot()

for s in root:
    family_annot_info_other = s[2].text
    family_annot_info_paint = s[3].text
    if family_annot_info_other or family_annot_info_paint:
        print(s[1].text)
        if family_annot_info_other:
            print(family_annot_info_other)

        if family_annot_info_paint:
            print(family_annot_info_paint)