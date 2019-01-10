from django.db import models

### Lookup tables ###

class ConfidenceCode(models.Model):
    confidence_code_sid = models.IntegerField(primary_key=True)
    confidence_code = models.CharField(max_length=16, blank=True, null=True)
    name = models.CharField(max_length=64, blank=True, null=True)
    evidence_requirement = models.CharField(max_length=1, blank=True, null=True)
    description = models.CharField(max_length=512, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'confidence_code'
        unique_together = (('confidence_code_sid', 'confidence_code_sid'),)

### GO tables ###
class GoClassification(models.Model):
    classification_id = models.DecimalField(primary_key=True, unique=True, max_digits=20, decimal_places=0, blank=True, null=False)
    classification_version_sid = models.DecimalField(max_digits=6, decimal_places=0, blank=True, null=True)
    depth = models.DecimalField(max_digits=2, decimal_places=0, blank=True, null=True)
    name = models.TextField(blank=True, null=True)
    accession = models.TextField(blank=True, null=True)
    definition = models.TextField(blank=True, null=True)
    created_by = models.DecimalField(max_digits=6, decimal_places=0, blank=True, null=True)
    creation_date = models.DateField(blank=True, null=True)
    obsoleted_by = models.DecimalField(max_digits=6, decimal_places=0, blank=True, null=True)
    obsolescence_date = models.DateField(blank=True, null=True)
    evalue_cutoff = models.CharField(max_length=32, blank=True, null=True)
    alt_acc = models.TextField(blank=True, null=True)
    term_type_sid = models.DecimalField(max_digits=6, decimal_places=0, blank=True, null=True)
    group_id = models.DecimalField(max_digits=6, decimal_places=0, blank=True, null=True)
    long_name = models.TextField(blank=True, null=True)
    revision_version_sid = models.DecimalField(max_digits=6, decimal_places=0, blank=True, null=True)
    replaced_by_acc = models.TextField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'go_classification'

class GoClassificationRelationship(models.Model):
    classification_relationship_id = models.DecimalField(primary_key=True, max_digits=20, decimal_places=0)
    parent_classification_id = models.DecimalField(max_digits=20, decimal_places=0)
    child_classification_id = models.DecimalField(max_digits=20, decimal_places=0)
    relationship_type_sid = models.DecimalField(max_digits=6, decimal_places=0, blank=True, null=True)
    rank = models.DecimalField(max_digits=6, decimal_places=0, blank=True, null=True)
    created_by = models.DecimalField(max_digits=6, decimal_places=0, blank=True, null=True)
    creation_date = models.DateTimeField(blank=True, null=True)
    obsoleted_by = models.DecimalField(max_digits=6, decimal_places=0, blank=True, null=True)
    obsolescence_date = models.DateTimeField(blank=True, null=True)
    overlap = models.DecimalField(max_digits=6, decimal_places=2, blank=True, null=True)
    overlap_unit = models.CharField(max_length=16, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'go_classification_relationship'

class GoAnnotation(models.Model):
    annotation_id = models.DecimalField(primary_key=True, unique=True, max_digits=38, decimal_places=0, blank=True, null=False, db_column='annotation_id')
    node_id = models.DecimalField(max_digits=38, decimal_places=0, blank=True, null=True)
    classification_id = models.DecimalField(max_digits=38, decimal_places=0, blank=True, null=True)
    annotation_type_id = models.DecimalField(max_digits=38, decimal_places=0, blank=True, null=True)
    created_by = models.DecimalField(max_digits=6, decimal_places=0, blank=True, null=True)
    creation_date = models.DateTimeField(blank=True, null=True)
    obsoleted_by = models.DecimalField(max_digits=6, decimal_places=0, blank=True, null=True)
    obsolescence_date = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'go_annotation'

class GoEvidence(models.Model):
    evidence_id = models.BigIntegerField(primary_key=True, unique=True, blank=True, null=False)
    evidence_type_sid = models.BigIntegerField(blank=True, null=True)
    classification_id = models.BigIntegerField(blank=True, null=True)
    primary_object_id = models.BigIntegerField(blank=True, null=True)
    evidence = models.CharField(max_length=1000, blank=True, null=True)
    is_editable = models.IntegerField(blank=True, null=True)
    created_by = models.CharField(max_length=64, blank=True, null=True)
    creation_date = models.DateTimeField(blank=True, null=True)
    obsoleted_by = models.CharField(max_length=64, blank=True, null=True)
    obsolescence_date = models.DateTimeField(blank=True, null=True)
    updated_by = models.CharField(max_length=64, blank=True, null=True)
    update_date = models.DateTimeField(blank=True, null=True)
    pathway_curation_id = models.BigIntegerField(blank=True, null=True)
    confidence_code_sid = models.IntegerField(blank=True, null=True, db_column='confidence_code_sid')
    annotation_id = models.DecimalField(max_digits=38, decimal_places=0, blank=True, null=True)
    protein_classification_id = models.BigIntegerField(blank=True, null=True)
    go_annotation = models.ForeignKey(GoAnnotation, to_field='annotation_id', on_delete=models.CASCADE)
    confidence_code = models.ForeignKey(ConfidenceCode, to_field='confidence_code_sid', on_delete=models.SET_NULL, null=True)

    class Meta:
        managed = False
        db_table = 'go_evidence'

class GoAnnotationQualifier(models.Model):
    annotation_qualifier_id = models.DecimalField(primary_key=True, max_digits=38, decimal_places=0, blank=True, null=False)
    annotation_id = models.DecimalField(max_digits=38, decimal_places=0, blank=True, null=True)
    qualifier_id = models.DecimalField(max_digits=38, decimal_places=0, blank=True, null=True)
    go_annotation = models.ForeignKey(GoAnnotation, to_field='annotation_id', on_delete=models.CASCADE)

    class Meta:
        managed = False
        db_table = 'go_annotation_qualifier'

### PAINT tables ###
class PaintAnnotation(models.Model):
    annotation_id = models.DecimalField(primary_key=True, unique=True, max_digits=38, decimal_places=0, blank=True, null=False)
    node_id = models.DecimalField(max_digits=38, decimal_places=0, blank=True, null=True)
    classification_id = models.DecimalField(max_digits=38, decimal_places=0, blank=True, null=True)
    annotation_type_id = models.DecimalField(max_digits=38, decimal_places=0, blank=True, null=True)
    created_by = models.DecimalField(max_digits=6, decimal_places=0, blank=True, null=True)
    creation_date = models.DateTimeField(blank=True, null=True)
    obsoleted_by = models.DecimalField(max_digits=6, decimal_places=0, blank=True, null=True)
    obsolescence_date = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'paint_annotation'

class PaintEvidence(models.Model):
    evidence_id = models.BigIntegerField(primary_key=True, blank=True, null=False)
    evidence_type_sid = models.BigIntegerField(blank=True, null=True)
    classification_id = models.BigIntegerField(blank=True, null=True)
    primary_object_id = models.BigIntegerField(blank=True, null=True)
    evidence = models.CharField(max_length=1000, blank=True, null=True)
    is_editable = models.IntegerField(blank=True, null=True)
    created_by = models.CharField(max_length=64, blank=True, null=True)
    creation_date = models.DateTimeField(blank=True, null=True)
    obsoleted_by = models.CharField(max_length=64, blank=True, null=True)
    obsolescence_date = models.DateTimeField(blank=True, null=True)
    updated_by = models.CharField(max_length=64, blank=True, null=True)
    update_date = models.DateTimeField(blank=True, null=True)
    pathway_curation_id = models.BigIntegerField(blank=True, null=True)
    # confidence_code_sid = models.IntegerField(blank=True, null=True)
    # annotation_id = models.BigIntegerField(blank=True, null=True)
    protein_classification_id = models.BigIntegerField(blank=True, null=True)
    paint_annotation = models.ForeignKey(PaintAnnotation, db_column='annotation_id', to_field='annotation_id', on_delete=models.CASCADE)
    confidence_code = models.ForeignKey(ConfidenceCode, db_column='confidence_code_sid', to_field='confidence_code_sid', on_delete=models.SET_NULL, null=True)
    # go_annotation from evidence if IBD
    # paint_annotation from evidence if IKR/IRD

    class Meta:
        managed = False
        db_table = 'paint_evidence'

class PaintAnnotationQualifier(models.Model):
    annotation_qualifier_id = models.DecimalField(primary_key=True, max_digits=38, decimal_places=0, blank=True, null=False)
    annotation_id = models.DecimalField(max_digits=38, decimal_places=0, blank=True, null=True)
    qualifier_id = models.DecimalField(max_digits=38, decimal_places=0, blank=True, null=True)
    paint_annotation = models.ForeignKey(PaintAnnotation, to_field='annotation_id', on_delete=models.SET_NULL, null=True)

    class Meta:
        managed = False
        db_table = 'paint_annotation_qualifier'