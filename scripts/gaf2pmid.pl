#!/usr/bin/perl

# $ gunzip gene-associations/*.gz
# $ rm gene-associations/*.json
# $ rm gene-associations/go_annotation_metadata.all.js

# $ cp gene-associations/submission/gene_association.gonuts.gz ~/go/gaf_archive/20171215/
# $ gunzip ~/go/gaf_archive/20171215/gene_association.gonuts.gz
# $ gzip ~/go/gaf_archive/20171215/*

# Raw submitted GAFs
# $ wget -A "-src.gaf.gz" http://release.geneontology.org/2018-12-01/products/annotations/


#use LWP 5.64;

#use LWP::Simple;

use utf8;

# use Text::Unidecode;



use Getopt::Std;

getopts('g:e');

my $gaf_dir = $opt_g if ($opt_g);       # -g for directory containing gaf files



# my $browser = LWP::UserAgent->new;	# What is this used for?

my @pmids;

opendir(GO, $gaf_dir) or die $!;

for my $gaf (readdir GO) {

    next if $gaf =~ /^\.\.?$/;

	#next unless $gaf eq 'goa_pig.gaf';

	open (GAF, "$gaf_dir/$gaf");

	while (my $line = <GAF>){

		next if ($line =~ /^!/);

		chomp($line);

		my ($dbname,$go_gid,$gsym,$qualifier,$goacc,$ref,$ev_code,$with,$gotype,$a,$b,$c,$tax1,@else) = split('\t', $line);

		$ref =~ s/^\s+|\s+$//g;

		next unless $ref =~ /PMID:/;

		#next unless $ref eq 'PMID:21680532';

		push (@pmids,($ref =~ /PMID:(\d+)/g));

	}

	close (GAF);

}

close (GO);



#push (@pmids, '21680532');

my %pmids = map { $_ => 1 } @pmids;



for my $id (keys %pmids){

	# print "http://amigo.geneontology.org/amigo/reference/$id\n";
	print "$id\n";

}