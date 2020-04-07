select u.name, count(*) from panther_upl.paint_annotation pa
join panther_upl.users u on u.user_id = pa.created_by 
where pa.creation_date > '{before_date}' and pa.creation_date < '{after_date}'
and obsolescence_date  is null
and exists (
	select 1 from panther_upl.paint_evidence pe 
	where pe.annotation_id = pa.annotation_id
	and pe.obsolescence_date is null
	and pe.confidence_code_sid = 15
)
group by u.name;