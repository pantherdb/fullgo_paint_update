ftp -n $PUBMED_HOST << EOT
user $PUBMED_USERID $PUBMED_PWORD
cd holdings

ls

get GO.uid $FULL_BASE_PATH/GO.uid
put $FULL_BASE_PATH/gaf2pmid_results /holdings/gaf2pmid_results
rename gaf2pmid_results GO.uid
EOT