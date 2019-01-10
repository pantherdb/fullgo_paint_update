
ftp -n $PUBMED_HOST << EOT
user $PUBMED_USERID $PUBMED_PWORD
cd holdings
get GO.uid
put gaf2pmid_results
rename gaf2pmid_results GO.uid
ls
EOT

# get GO.uid
# put $FULL_BASE_PATH/gaf2pmid_results
# rename gaf2pmid_results GO.uid