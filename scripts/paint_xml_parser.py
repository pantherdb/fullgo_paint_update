from xml.etree import ElementTree
from argparse import ArgumentParser

parser = ArgumentParser()
parser.add_argument("filepath")
args = parser.parse_args()

### Clean up xml format
filepath = args.filepath
with open(filepath) as f:
    raw_xml = f.read()

xml_header = raw_xml.split("\n")[0]
new_xml = raw_xml.replace(xml_header + "\n", "")
root_tag = new_xml.split("\n")[0]
if root_tag != "<searches>":
    new_xml = "<searches>\n" + new_xml
    new_xml = new_xml + "</searches>\n"
new_xml = "<?xml version=\"1.0\"?>\n" + new_xml

with open(filepath, "w") as wf:
    wf.write(new_xml)

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