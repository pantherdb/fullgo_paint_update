from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from django.conf import settings
from paintdb.models import PaintEvidence, GoAnnotation, GoEvidence
import csv
import datetime

def test_method(exp_annot_file, paint_ev_file):
    print("Exp GO file is:", exp_annot_file)
    print("Paint evidence file is:", paint_ev_file)

class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument('exp_annot_file')
        parser.add_argument('paint_ev_file')

    def handle(self, *args, **options):
        # print(options)
        # test_method(options['exp_annot_file'], options['paint_ev_file'])
        check_invalid_paint_evidence(options['exp_annot_file'], options['paint_ev_file'])

NOT_QUALIFIER_ID = '62114966'

# paint_evidences = PaintEvidence.objects.filter(obsolescence_date=None)
# print("# of non-obsolete paint evidence records = {}".format(len(paint_evidences)))


def load_annot_dict(filename, evidence=False):
    annot_file = open(filename)
    reader = csv.reader(annot_file, delimiter=";")
    # Make index file with just annotation_ids?
    annot_dict = {}
    next(reader) # skip column row
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

def check_invalid_paint_evidence(exp_annot_file, paint_ev_file):
    go_exps = load_annot_dict(exp_annot_file)
    # paint_evs = load_annot_dict("../resources/paint_evs.txt", evidence=True)
    paint_evs = load_annot_dict(paint_ev_file, evidence=True)

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
                # Check for difference in NOTs
                # if len(paint_qualifiers) > 1 or len(go_qualifiers) > 1:
                #     print(paint_qualifiers)
                #     print(go_qualifiers)
                #     break
                if NOT_QUALIFIER_ID in paint_qualifiers and NOT_QUALIFIER_ID not in go_qualifiers:
                    evidence_ids_to_obsolete.append(ev_id)
                elif NOT_QUALIFIER_ID in go_qualifiers and NOT_QUALIFIER_ID not in paint_qualifiers:
                    evidence_ids_to_obsolete.append(ev_id)
                # elif paint_qualifiers != go_qualifiers:
                #     evidence_ids_to_obsolete.append(ev_id)
                else:
                    # print("We good")
                    do_nothing = 1
        else:
            for ev_id in paint_evs[ev]:
                evidence_ids_to_obsolete.append(ev_id)

    evidence_ids_to_obsolete = list(set(evidence_ids_to_obsolete))
    print("# of evidence_ids to obsolete: {}".format(len(evidence_ids_to_obsolete)))

    for e in evidence_ids_to_obsolete:
        PaintEvidence._meta.db_table = 'paint_evidence_new'
        todays_date = datetime.datetime.now()
        # paint_evidence = PaintEvidence.objects.get(pk=e)
        # paint_evidence.obsolescence_date = timezone.make_aware(todays_date)
        # paint_evidence.obsoleted_by = '1'
        # paint_evidence.save()
        PaintEvidence.objects.filter(pk=e).update(obsolescence_date=timezone.make_aware(todays_date), obsoleted_by='1')
        # print(paint_evidence.obsolescence_date)
        # print(e)