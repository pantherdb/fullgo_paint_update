-- For testing https://github.com/pantherdb/fullgo_paint_update/issues/12
-- Should not be null
set search_path = panther_upl;
select obsolescence_date from go_classification
where accession = 'GO:0042787';

-- Should be 0
set search_path = panther_upl;
select count(*) from go_annotation ga
join go_classification gc on gc.classification_id = ga.classification_id
where gc.accession = 'GO:0042787';