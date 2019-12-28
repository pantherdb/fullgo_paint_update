--copy data to new table to be updated, old table serve as a backup, try to keep the evidence_id that didn't change
set search_path = panther_upl;
--due to the _fix table switcheroos the _new tables will always be hanging around
ALTER TABLE paint_evidence_old RENAME TO paint_evidence_new;
truncate table paint_evidence_new;
insert into paint_evidence_new select * from paint_evidence;

--Go through the paint_evidence table, for all evidence type as 46 (paint EXP), the evidence can be forwardly tracked to go_annotation entries with obsolescence_date as null in full GO annotation table. If not, mark the evidence as obsoleted.
set search_path = panther_upl;
update paint_evidence_new pen 
set obsoleted_by = 1, obsolescence_date = now() 
where not exists ( 
    select 1 from go_annotation_new gan 
    join go_evidence_new gen on gen.annotation_id = gan.annotation_id
    join confidence_code cc on cc.confidence_code_sid = gen.confidence_code_sid
    left join go_evidence_qualifier_new geq on geq.evidence_id = gen.evidence_id
    left join paint_annotation_qualifier paq on paq.annotation_id = pen.annotation_id
    where cast(pen.evidence as int) = gan.annotation_id 
    and gan.obsolescence_date is null
    and cc.confidence_code in ('EXP', 'IDA', 'IPI', 'IMP', 'IGI', 'IEP', 'HTP', 'HDA', 'HMP', 'HGI', 'HEP')
    and (geq.qualifier_id = paq.qualifier_id or (geq.evidence_qualifier_id is null and paq.annotation_qualifier_id is null))
  ) 
  and pen.obsolescence_date is null;

-- Global insert of all valid 'withs' for a paint_annotation, checking exp evidence on any descendant nodes to same term or descendant term if 'with' doesn't exist
-- Could this potentially un-obsolete redundant IBDs that we fix? Not if they're manually obsoleted
insert into paint_evidence_new(evidence_id, evidence_type_sid, evidence, created_by, creation_date, confidence_code_sid, annotation_id)
select nextval('uids'), 46, x.go_annotation_id::varchar(255), 1, now(), 15, x.paint_annotation_id from
(select distinct ga.annotation_id go_annotation_id, pa.annotation_id paint_annotation_id, gcp.accession, gcg.accession, g.primary_ext_acc
from
(select parent_node_acc, unnest(string_to_array(child_leaf_node_acc, ',')) as leaf from node_all_leaves_v14_1) pl
join node n on n.accession = pl.parent_node_acc
join node n1 on n1.accession = pl.leaf
join paint_annotation_new pa on pa.node_id = n.node_id
join go_classification_descendants dd on dd.parent_classification_id = pa.classification_id
join go_annotation_new ga on ga.node_id = n1.node_id and (ga.classification_id = pa.classification_id or ga.classification_id::varchar(255) = any(string_to_array(dd.desc_classification_ids, ','))) -- all GO annots to any leaf node with any descendant term
join paint_evidence_new pe on pe.annotation_id = pa.annotation_id
join go_evidence_new ge on ge.annotation_id = ga.annotation_id
join confidence_code cc on cc.confidence_code_sid = ge.confidence_code_sid
left join go_evidence_qualifier_new geq on geq.evidence_id = ge.evidence_id
left join paint_annotation_qualifier paq on paq.annotation_id = pa.annotation_id
join go_classification_new gcp on gcp.classification_id = pa.classification_id
join go_classification_new gcg on gcg.classification_id = ga.classification_id
join gene_node gn on gn.node_id = n1.node_id
join gene g on g.gene_id = gn.gene_id
where pe.evidence_type_sid = 46  -- still need paint_evidence to isolate IBDs - we can allow obsolete paint_evidences too
and n.classification_version_sid = {classification_version_sid}
and n1.classification_version_sid = {classification_version_sid}
and ga.annotation_id != pe.annotation_id
and ga.obsolescence_date is null
and (pa.obsoleted_by = 1 or pa.obsoleted_by is null) -- Only touch annotations non-obsolete or obsoleted by system
and (geq.qualifier_id = paq.qualifier_id or (geq.evidence_qualifier_id is null and paq.annotation_qualifier_id is null))
and cc.confidence_code in ('EXP', 'IDA', 'IPI', 'IMP', 'IGI', 'IEP', 'HTP', 'HDA', 'HMP', 'HGI', 'HEP')
) x
-- Move this into x?
where not exists (
	select 1 from paint_evidence_new
	where annotation_id = x.paint_annotation_id and evidence = x.go_annotation_id::varchar(255)
	and evidence_type_sid = 46 and confidence_code_sid = 15
	and obsolescence_date is null
);

--Update evidence column to correct, non-obsolete GO annotation for PAINT ANCESTOR evidence records and mark un-obsoleted
set search_path=panther_upl;
update paint_evidence_new pen
set evidence = x.ancestor_paint_annotation_id, obsolescence_date = null, obsoleted_by = null
from
(
  select distinct pan.annotation_id child_paint_annotation_id, pan1.annotation_id ancestor_paint_annotation_id, pe.evidence_id
  from
  (
    select child_node_acc, unnest(string_to_array(ancestor_node_acc, ',')) as ancestor from node_all_ancestors_v14_1
  ) ca, paint_annotation_new pan, node n, node n1, paint_annotation_new pan1, paint_evidence_new pe
  where pan.node_id = n.node_id
  and n.accession = ca.child_node_acc
  and n1.node_id = pan1.node_id
  and n1.accession = ca.ancestor
  and pan.classification_id = pan1.classification_id
  and pan1.obsolescence_date is null
  and pan.annotation_id = pe.annotation_id
  and pe.evidence_type_sid = 47
  and n.classification_version_sid = {classification_version_sid}
  and n1.classification_version_sid = {classification_version_sid}
) x
where pen.evidence_id = x.evidence_id
and pen.obsolescence_date is not null
and pen.obsoleted_by = '1';

-- Go through the paint-annotation table, and see if this annotation_id is still exist in the paint_evidence table with obsoleted_by column is null, if not, obsolete the paint_annotation entry
set search_path=panther_upl;
update paint_annotation_new pa 
set obsoleted_by = 1, obsolescence_date = now() 
from paint_evidence_new pe 
where pa.annotation_id not in (
    select pe.annotation_id 
    from paint_evidence_new pe, paint_annotation_new pa 
    where pe.annotation_id = pa.annotation_id 
    and pe.evidence_type_sid = 46 
    and pe.obsoleted_by is null
  ) 
  and pa.annotation_id = pe.annotation_id 
  and pe.evidence_type_sid = 46 
  and pa.obsolescence_date is null;

-- Spit out list of unobsoleted IBDs before update below
set search_path=panther_upl;
select count(distinct(pan.annotation_id)) from  paint_annotation_new pan
join paint_evidence_new pen on pen.annotation_id = pan.annotation_id
where pan.obsolescence_date is not null
and pan.obsoleted_by = 1
and pen.obsolescence_date is null;

-- If paint_annotation is obsolete (by update pipeline) and associated, non-obsolete paint_evidence exists, then un-obsolete paint_annotation.
set search_path=panther_upl;
update paint_annotation_new pan
set obsoleted_by = null, obsolescence_date = null
from paint_evidence_new pen
where pen.annotation_id = pan.annotation_id
and pan.obsolescence_date is not null
and pan.obsoleted_by = 1
and pen.obsolescence_date is null;