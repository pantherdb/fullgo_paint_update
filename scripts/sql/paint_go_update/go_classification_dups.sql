--find if there are duplicated data in the table
set search_path = panther_upl;

select * from (  
  SELECT accession,  ROW_NUMBER() OVER(PARTITION BY accession, definition ORDER BY accession asc) AS Row  
  FROM go_classification_new 
  ) dups 
  where dups.Row > 1;

set search_path = panther_upl;

select * from 
  (
    SELECT classification_relationship_id,parent_classification_id,child_classification_id,
      ROW_NUMBER() OVER(PARTITION BY parent_classification_id, child_classification_id, relationship_type_sid ORDER BY parent_classification_id,child_classification_id asc) AS Row 
    FROM go_classification_relationship_new
  ) dups 
  where dups.Row > 1;

set search_path = panther_upl;
delete from go_classification_relationship_new 
where classification_relationship_id in (
  select classification_relationship_id from 
  (
    SELECT classification_relationship_id,parent_classification_id,child_classification_id, 
      ROW_NUMBER() OVER(PARTITION BY parent_classification_id, child_classification_id, relationship_type_sid ORDER BY parent_classification_id,child_classification_id asc) AS Row 
    FROM go_classification_relationship_new
  ) dups 
  where  dups.Row > 1
);