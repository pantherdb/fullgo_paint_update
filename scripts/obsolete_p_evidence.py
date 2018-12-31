# from paintdb.models import PaintEvidence, GoAnnotation, GoEvidence
import csv
import argparse

parser = argparse.ArgumentParser()
parser.add_argument('-g', '--exp_annot_file')
parser.add_argument('-p', '--paint_ev_file')

# paint_evidences = PaintEvidence.objects.filter(obsolescence_date=None)
# print("# of non-obsolete paint evidence records = {}".format(len(paint_evidences)))


def load_annot_dict(filename, evidence=False):
    annot_file = open(filename)
    reader = csv.reader(annot_file, delimiter=";")
    # Make index file with just annotation_ids?
    annot_dict = {}
    for r in reader:
        if evidence:
            thing_to_append = (r[1], r[2])
            if r[0] in annot_dict:
                if thing_to_append[1] in annot_dict[r[0]]:
                    annot_dict[r[0]][thing_to_append[1]].append(thing_to_append[0])
                else:
                    annot_dict[r[0]][thing_to_append[1]] = [thing_to_append[0]]
            else:
                annot_dict[r[0]] = {}
                annot_dict[r[0]][thing_to_append[1]] = [thing_to_append[0]]
        else:
            thing_to_append = r[1]
            if r[0] in annot_dict:
                annot_dict[r[0]].append(thing_to_append)
            else:
                annot_dict[r[0]] = [thing_to_append]
    annot_file.close()
    return annot_dict

args = parser.parse_args()

go_exps = load_annot_dict(args.exp_annot_file)
# paint_evs = load_annot_dict("../resources/paint_evs.txt", evidence=True)
paint_evs = load_annot_dict(args.paint_ev_file, evidence=True)

total_count = len(paint_evs)
counter = 0
top_current_percent = 0
evidence_ids_to_obsolete = []
for ev in paint_evs:
    # Maybe filter out IKR/IRDs?
    counter += 1
    current_percent = int((counter / total_count) * 100)
    # print(counter)
    if current_percent > top_current_percent:
        top_current_percent = current_percent
        # print("{}%".format(top_current_percent))
    if ev in go_exps:
        go_qualifiers = go_exps[ev]
        go_qualifiers = list(set(go_qualifiers))
        go_qualifiers = list(filter(None, go_qualifiers))
        for ev_id in paint_evs[ev]:
            # Check for whatever equivalence then append evidence_id to list if it fails
            paint_qualifiers = paint_evs[ev][ev_id]
            paint_qualifiers = list(set(paint_qualifiers))
            paint_qualifiers = list(filter(None, paint_qualifiers))
            # print(go_qualifiers)
            # print(paint_qualifiers)
            if paint_qualifiers != go_qualifiers:
                # print("Nope")
                evidence_ids_to_obsolete.append(ev_id)
            else:
                # print("We good")
                do_nothing = 1
    else:
        for ev_id in paint_evs[ev]:
            evidence_ids_to_obsolete.append(ev_id)

evidence_ids_to_obsolete = list(set(evidence_ids_to_obsolete))
print("# of evidence_ids to obsolete: {}".format(len(evidence_ids_to_obsolete)))

for e in evidence_ids_to_obsolete[0:10]:
    print(e)