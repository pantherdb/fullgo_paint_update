#!/usr/bin/perl 
format HEADER =
/ -----------------------------------------------------------------------------------
| Purpose : Creating program to extract information from Gene Ontology file			|
| 																					|	
|  Options:																			|
|    -v    verbose mode																|
|    -d    debug mode																|
|    -t    test mode																|
|    -h    Give help screen															|
|  																					|
\ ----------------------------------------------------------------------------------
.
 
#
# History
# ----------------------------
# Written by: Sagar Poudel   #  
# Created Date: 07/31/14  	#
# Updated date:	08/10/15	#
# updated : 05/25/2016 by Xiaosong Huang #
# updated: 02/27/2017 by Xiaosong Huang
# updated: 10/30/2017 by XH for adding alt_id field
#----------------------------
#use strict;

use Getopt::Std;
getopts('h:i:o:e:v:V') || &usage();
&usage() if ($opt_h);          # -h for (h)elp
$input = $opt_i if ($opt_i);   # -i for (i)NPUT File
$output = $opt_o if ($opt_o);  # -o for (o)utput
$errFile = $opt_e if ($opt_e); # -e for (e)rror file (redirect STDERR)
$verbose = 1 if ($opt_v);      # -v for (v)erbose (debug info to STDERR)
$verbose = 2 if ($opt_V);      # -V for (V)ery verbose (debug info to STDERR)


open(GO, $input) or die $!;
open(OUT, ">$output") or die $!;


my @obsolete_terms;
my %replaced_terms;
my %all_alt_ids;

local $/="[Term]";

my $headers = <GO>;
my @header_lines = split(/\n/,$headers);
my $release_date;
for my $header (@header_lines){
    chomp $header;
	if ($header =~ /^data\-version:/){
	   #print "$header\n";
	   ($release_date) = $header =~ /(\d+\-\d+\-\d+)/;
	   $release_date =~ s/\-/:/g;
	   #print "$release_date\n";
	}
}

print OUT "Accession\tName\tTermTypeSID\tDefinition\tObsolete_date\tReplaced_by\tAlt_id\n";
while (my $record=<GO>){
    my $def;
    my @alt_id;
	my @lines=split(/\n/, $record);
	my $gid=(split(/id:/, $lines[1]))[1];
	#print "$gid\n";
	$gid=~ s/^\s+|\s+$//g;
	#print "$gid\n";
	my $name=(split(/name:/, $lines[2]))[1];
	$name =~ s/^\s+|\s+$//g;
	my $ttype=(split(/namespace:/, $lines[3]))[1];
	my $obsolete_date;
	my $replace_term;
	for my $line (@lines) {
		if ($line =~ /^def:/) {
		   $def=(split(/def:/, $line))[1];
		   $def =~ s/^\s+|\s+$//g; 
		}
		if ($line =~ /^alt_id:/) {
			my $alt_id = (split(/alt_id:/, $line))[1];
			$alt_id =~ s/^\s+|\s+$//g;
			push (@alt_id, $alt_id); 
			$all_alt_ids{$alt_id}=$gid;
		}
		if ($line =~ /^is_obsolete/i){
			#print "$line\n";
			push (@obsolete_terms, $gid) if $line =~ /true/i;
			#print "$gid\n" if $line =~ /true/i;
			#print "$gid\n";
			$obsolete_date = $release_date;
		}
		if ($line =~ /^replaced_by/i){
		    chomp $line;
			($replace_term) = $line =~ /(GO\:\d+)/;
			$replaced_terms{$gid}=$replace_term;
		}
    }

	
	$name =~ s/^\s+|\s+$//g;
	$ttype=~ s/^\s+|\s+$//g;
	$def =~ s/\"//g;
	$def =~ s/^\s+|\s+$//g;
	$obsolete_date =~ s/^\s+|\s+$//g;
	$replace_term =~ s/^\s+|\s+$//g;
	
	if($ttype eq 'molecular_function'){
		 $ttype=14;
		 }
	elsif($ttype eq 'biological_process'){
		 $ttype=12;
		 }
	elsif($ttype eq 'cellular_component'){
		$ttype=13;
		 }
	if($gid ne ""){
	    if (@alt_id){
		   for my $alt_id (@alt_id){
		       $alt_id =~ s/^\s+|\s+$//g;
		       print OUT "$gid\t$name\t$ttype\t$def\t$obsolete_date\t$replace_term\t$alt_id\n";
			   #print "$gid\t$name\t$ttype\t$def\t$obsolete_date\t$replace_term\t$alt_id\n";
		   }
		}else{
	       print OUT "$gid\t$name\t$ttype\t$def\t$obsolete_date\t$replace_term\t\n";
		   #print "$gid\t$name\t$ttype\t$def\t$obsolete_date\t$replace_term\t\n";
		}
	}
	
	# for my $alt_id (@alt_id){
	   # $alt_id=~ s/^\s+|\s+$//g;
	   # if ($alt_id ne ""){
	       # print OUT "$alt_id\t$name\t$ttype\t$def\t$obsolete_date\t$replace_term\n";
	   # }
	# }
}
close(GO,OUT);
#close(GO);
for my $obsolete (@obsolete_terms){
   #print "$obsolete\n";
   my $replace_term;
   if (defined $replaced_terms{$obsolete}){
       $replace_term = $replaced_terms{$obsolete};
   }
   print "$obsolete\t$replace_term\n";
}
for my $alt_id (keys %all_alt_ids){
	my $replace_term = $all_alt_ids{$alt_id};
	print "$alt_id\t$replace_term\n";
}
# output for help and errors
sub usage {
    my $error = shift;

    print <<__EOT;

extractfromobo.pl - a program to extract information from go.obo file

Usage:
    extractfromobo.pl -i input data file name (go.obo) -o output file name (inputforGOClassification-0815.tsv)

Where args are:
\t-h for help (this message)
\t-i for (i)NPUT File
\t-o -o for (o)utput
\t-e (e)rror file (redirect STDERR)
\t-v (v)erbose (debug info to STDERR)
\t-V (V)ery verbose (debug info to STDERR)

__EOT

  print "Error: $error\n\n" if ($error);

  exit(-1);
}


 