#!/usr/bin/perl
# use strict;

BEGIN { $ENV{LIST_MOREUTILS_PP}=1; }
use Carp;
use List::MoreUtils qw(uniq);
use Time::localtime;

my %go_id_to_pthrid;
my %uniprot_id_to_pthrid;
my %alterid_to_pthrid;
my %gene_symbol_taxa_to_pthrid;
my %gene_symbol_db_to_pthrid;
my %pthrid_to_taxid;
my %taxon;
my %gomf;
my %gomfw;
my %gomf_exp;
my %gobp;
my %gobpw;
my %gobp_exp;
my %gocc;
my %goccw;
my %gocc_exp;
my %goempty;
my @all_pthrid;
my @matched_ptherid;
my @unmatched_ptherid;
my %golist;

use Getopt::Std;
getopts('h:f:t:i:g:p:m:o:x:b:c:d:y:a:u:e:v:w:H:P:M:B:C:V') || &usage();
&usage() if ($opt_h);          # -h for (h)elp
$fullgo = $opt_f if ($opt_f);   # -f for (f) full gene Ontology association complete File (GAF file)
$dir = $opt_d if ($opt_d);	# -d for base directory. where files will be saved
$tax = $opt_t if ($opt_t);  # -t for (t)axon File (organism.dat)
$ide = $opt_i if ($opt_i);   # -i for (i)dentifier File
$gen = $opt_g if ($opt_g);  # -g for (g)ene File
$xcode = $opt_x if ($opt_x);  # -x for e(x)perimental codes File
$pc = $opt_p if ($opt_p);  # -p for (p)arent child relation  File
$pthr_version = $opt_P if ($opt_P);  # -P for Panther version
$mf = $opt_M if ($opt_M);   # -M for (m)oleculer Function annotation (without 'not' annotation) output File
$bp = $opt_B if ($opt_B);  # -B for (b)iological process annotation (without 'not' annotation) output File
$cc = $opt_C if ($opt_C);  # -C for (c)ellular component annotation (without 'not' annotation) output File
$mfe = $opt_m if ($opt_m);   # -m for experimental (m)oleculer Function output File
$bpe = $opt_b if ($opt_b);  # -b for experimental (b)iological process output File
$cce = $opt_c if ($opt_c);  # -c for experimental (c)ellular component output File
$goannow = $opt_w if ($opt_w); # -w for complete go annotation mapped to pthr (with evidence) output file
$hierarchy_suffix = $opt_H if ($opt_H); # -H suffix at end of hierarchy output files. Holds Pthr version and/or Proc ID
$emty = $opt_y if ($opt_y); # -y for pantherid with empty go terms output File
$mat = $opt_a if ($opt_a);   # -a for total m(a)tch File
$umat = $opt_u if ($opt_u);  # -u for total (u)nmatch Data File
$go = $opt_o if ($opt_o); # -o for go.obo file
$errFile = $opt_e if ($opt_e); # -e for (e)rror file (redirect STDERR)
$verbose = 1 if ($opt_v);      # -v for (v)erbose (debug info to STDERR)
$verbose = 2 if ($opt_V);      # -V for (V)ery verbose (debug info to STDERR)

open(GEN, $gen) or die $!;
for (<GEN>) {};
$gene_file_count = $.;
print STDERR "gene.dat file: $gene_file_count\n";
open(GEN, $gen) or die $!;
opendir(GO, $fullgo) or die $!;
open(TAX, $tax) or die $!;
open(ID, $ide) or die $!;
for (<ID>) {};
$id_file_count = $.;
print STDERR "identifiers.dat file: $id_file_count\n";
open(ID, $ide) or die $!;
open(GOT, $go) or die $!;
open(GOW, ">$goannow") or die $!;
open(STDERR, ">$errFile") or die $!;
print STDERR "Opened arg files\n";

open CP, "<$dir/FinalChildParent-Hierarchy.dat" or die $!;
# open FN1, ">$dir/GOWithHierarchy-BP-$pthr_version.dat" or die $!;
open FN1, ">$dir/GOWithHierarchy-BP-$hierarchy_suffix" or die $!;
open FN2, ">$dir/GOWithHierarchy-MF-$hierarchy_suffix" or die $!;
open FN3, ">$dir/GOWithHierarchy-CC-$hierarchy_suffix" or die $!;
print FN1 "SequenceID\tGOHierarchy\tEvidenceCode\tWith\tReference\tDate\tDB\n";
print FN2 "SequenceID\tGOHierarchy\tEvidenceCode\tWith\tReference\tDate\tDB\n";
print FN3 "SequenceID\tGOHierarchy\tEvidenceCode\tWith\tReference\tDate\tDB\n";

while (<TAX>) 
{
	 chomp($_);
	# Parsing organism.dat
	my ($organism, $conversion, $code, $name, $common_name, $taxid, @rest) = split('\t');
	chomp($code,$taxid);
	$taxid =~ s/^\s+|\s+$//g;
	$code =~ s/^\s+|\s+$//g;
	
	$taxon{$code}=$taxid;	
	
}
	
close(TAX);
print STDERR "Loaded taxonomy file\n";

while (<CP>) 
	{
	chomp($_);
	my ($child,$parents) = split('\t');
	chomp($child,$parents);
	$golist{$child}=$parents;
    #print "$child\t$parents\n";
	}
close(CP);	

my %obso_go;
{
local $/="[Term]";
while (my $record=<GOT>){
    my $def;
    my @alt_id;
	my @lines=split(/\n/, $record);
	my $goid=(split(/id:/, $lines[1]))[1];
	#print "$gid\n";
	$goid=~ s/^\s+|\s+$//g;
	#print "$gid\n";
	my $name=(split(/name:/, $lines[2]))[1];
	my $ttype=(split(/namespace:/, $lines[3]))[1];
	my $obsolete_term;
	my $replace_term;
	for my $line (@lines) {
		if ($line =~ /^def:/) {
		   $def=(split(/def:/, $line))[1];
		}
		if ($line =~ /^alt_id:/) {
			push (@alt_id, (split(/alt_id:/, $line))[1]);
		}
		if ($line =~ /^is_obsolete/i){
			$obsolete_term = $goid if $line =~ /true/i;
			#print "$obsolete_term\n";
		}
		if ($line =~ /^replaced_by/i){
		    chomp $line;
			($replace_term) = $line =~ /(GO\:\d+)/;
			#print "$replace_term\n";
		}
    }

	if ($obsolete_term){
	   $obso_go{$obsolete_term}=$replace_term;
	   #print "$obsolete_term\t$replace_term\n"
	}
	
}
close(GOT);
}
print STDERR "Loaded ontology file\n";

$gen_counter = 0;
$gen_percent = 0;
while (<GEN>) 
	 {
	 chomp($_);
	 my ($pthrid,$geneDesc,$geneSym) = split('\t');
	 chomp($geneDesc,$pthrid,$geneSym);
	 $geneSym =~ s/^\s+|\s+$//g;
	 
	 $pthrid =~ s/^\s+|\s+$//g;
	 
	 #push (@all_pthrid, $pthrid);
	 my ($org,$gene,$protein) = split('\|',$pthrid);
	 chomp($org, $gene, $protein);
	 $org =~ s/^\s+|\s+$//g;
	 my $tax = $taxon{$org};
	 print STDERR "$org is missed in taxon code to taxID mapping file." unless ($tax);
	 
	 my ($unitpro,$unitpro_id)=split('=',$protein);
	 chomp($unitpro,$unitpro_id);
	 $unitpro_id =~ s/^\s+|\s+$//g;
	 
	 $uniprot_id_to_pthrid{$unitpro_id} = $pthrid;
	 $go_id_to_pthrid{$unitpro_id}{'UniProtKB'} = $pthrid;
	 $go_id_to_pthrid{$unitpro_id}{$tax} = $pthrid;
	 if ($gene =~ /'MGI=MGI'/){
	    my $mgiid=(split('=', $gene))[-1];
		$mgiid = 'MGI:'.$mgiid;
		
		$go_id_to_pthrid{$mgiid}{'MGI'} = $pthrid;
		$go_id_to_pthrid{$mgiid}{$tax} = $pthrid;
	 }
	 else {
	    my ($dbname, $gene_id1, $gene_id2) = split('=', $gene);
		
	    $go_id_to_pthrid{$gene_id1}{$dbname} = $pthrid;
		$go_id_to_pthrid{$gene_id1}{$tax} = $pthrid;
		if (defined $gene_id2){
		    $go_id_to_pthrid{$gene_id2}{$dbname} = $pthrid;
			$go_id_to_pthrid{$gene_id2}{$tax} = $pthrid;
		}
	 
	 }
	 
	 $pthrid_to_taxid{$pthrid} = $tax;
	 $gene_symbol_taxa_to_pthr{$geneSym}{$tax} = $pthrid;
	 $gene_symbol_db_to_pthr{$geneSym}{$dbname} = $pthrid;

	$gen_counter++;
	$new_gen_percent = int($gen_counter / $gene_file_count * 100);
	if ($new_gen_percent > $gen_percent) {
		$gen_percent = $new_gen_percent;
		print STDERR "$gen_percent\% of gene file is parsed\n";
	}
 	}	
close(GEN);
print STDERR "Loaded gene.dat file\n";

$id_counter = 0;
$id_percent = 0;
while (<ID>){
	chomp($_);
	my ($unipro_id,$db,$alter_id) = split('\t');
	chomp($unipro_id,$db,$alter_id);
	$alter_id =~ s/^\s+|\s+$//g;
	$unipro_id =~ s/^\s+|\s+$//g;
	my $pthrid = $uniprot_id_to_pthrid{$unipro_id};
	my ($org,$gene,$protein) = split('\|',$pthrid);
	chomp($org, $gene, $protein);
	$org =~ s/^\s+|\s+$//g;
	my $tax = $pthrid_to_taxid{$pthrid};
	print STDERR "$pthrid missing taxon code to taxID mapping." unless ($tax);
	$alterid_to_pthrid{$alter_id}{$db} = $pthrid;
	$alterid_to_pthrid{$alter_id}{$tax} = $pthrid;

	$id_counter++;
        $new_id_percent = int($id_counter / $id_file_count * 100);
        if ($new_id_percent > $id_percent) {
                $id_percent = $new_id_percent;
                print STDERR "$id_percent\% of identifier file is parsed\n";
        }
}
	
close(ID);
print STDERR "Loaded indentifier.dat file\n";


my %refre;
print STDERR "pthr_id\tmap_go_gid\tmap_by\t\tmap_by_comb\tgo_term\tgo_type\n";
for my $gaf (readdir GO) {
    next if $file =~ /^\.\.?$/;
	print "working on $gaf\n";
	open (GAF, "$fullgo/$gaf");
	print STDERR "Parsing file: $gaf";
    while (<GAF>) {
	      next if ($_ =~ /^!/);
		  chomp($_);
		  my ($dbname,$go_gid,$gsym,$qualifier,$goacc,$ref,$ev_code,$with,$gotype,$a,$b,$c,$tax1,$date,$contrib_group,@else) = split('\t');
	      chomp($dbname,$go_gid,$gsym,$qualifier,$goacc,$ref,$ev_code,$with,$gotype,$a,$b,$c,$tax1,$date,$contrib_group);
	      $go_gid =~ s/^\s+|\s+$//g;
	      $dbname =~ s/^\s+|\s+$//g;
	      $gotype =~ s/^\s+|\s+$//g;
		  $gotype = 'molecular_function' if $gotype eq 'F';
		  $gotype = 'biological_process' if $gotype eq 'P';
		  $gotype = 'cellular_component' if $gotype eq 'C';
	      $gsym =~ s/^\s+|\s+$//g;
		  $goacc =~ s/^\s+|\s+$//g;
		  $contrib_group =~ s/^\s+|\s+$//g;
		  if (defined $obso_go{$goacc}){
		     my $repl_term = $obso_go{$goacc};
			 $goacc=$repl_term;
		  }
		  next if ($goacc eq '');
		  if ($gsym =~ /\|/g){
		    #print "$gsym\t";
			$gsym =~ s/\|/\\/g;
		  }
		  $qualifier = &checkQualifier($qualifier);
		  
		  $tax1 =~ s/^\s+|\s+$//g;
		  my ($taxon, $tax) = split(':', $tax1);
		  $tax =~ s/^\s+|\s+$//g;
		  my %mapped_pthrid;
		  if(($dbname eq 'UniProtKB') && (exists $uniprot_id_to_pthrid{$go_gid} && defined $uniprot_id_to_pthrid{$go_gid})){
		      #print MAT "$_\n";
			  my $pthrid = $uniprot_id_to_pthrid{$go_gid};
			  #print STDERR "$pthrid\t$go_gid\tUniProtKB_ID plus dbname\t$go_gid\|$dbname\t$goacc\t$gotype\n";
			  #$mapped_pthrid{$pthrid}++;
			  #push(@matched_ptherid, $pthrid);
			  &addAnnotDetails($pthrid, $goacc, $ev_code, $with, $ref, $date, $contrib_group);
			  &goToPthr($pthrid,$gotype,$goacc,$qualifier, $ev_code, $with, $ref, $date, $contrib_group);
		  }
		  elsif(((exists $go_id_to_pthrid{$go_gid}{$dbname}) && (defined $go_id_to_pthrid{$go_gid}{$dbname}))){
		      #print MAT "$_\n";
			  my $pthrid = $go_id_to_pthrid{$go_gid}{$dbname};
			  #print STDERR "$pthrid\t$go_gid\tPanther_Middle_ID plus dbname\t$go_gid\|$dbname\t$goacc\t$gotype\n";
			  #$mapped_pthrid{$pthrid}++;
			  #push(@matched_ptherid, $pthrid);
			  &addAnnotDetails($pthrid, $goacc, $ev_code, $with, $ref, $date, $contrib_group);
			  &goToPthr($pthrid,$gotype,$goacc,$qualifier, $ev_code, $with, $ref, $date, $contrib_group);
		  }
		  elsif(((exists $go_id_to_pthrid{$go_gid}{$tax}) && (defined $go_id_to_pthrid{$go_gid}{$tax}))){
		      #print MAT "$_\n";
			  my $pthrid = $go_id_to_pthrid{$go_gid}{$tax};
			  #print STDERR "$pthrid\t$go_gid\tPanther_Middle_ID plus taxon_id\t$go_gid\|$tax\t$goacc\t$gotype\n";
			  
			  
			  #$mapped_pthrid{$pthrid}++;
			  #push(@matched_ptherid, $pthrid);
			  &addAnnotDetails($pthrid, $goacc, $ev_code, $with, $ref, $date, $contrib_group);
			  &goToPthr($pthrid,$gotype,$goacc,$qualifier, $ev_code, $with, $ref, $date, $contrib_group);
		  }
		  
		  elsif (((exists $alterid_to_pthrid{$go_gid}{$dbname}) && (defined $alterid_to_pthrid{$go_gid}{$dbname}))){
		      #print MAT "$_\n";
			  my $pthrid = $alterid_to_pthrid{$go_gid}{$dbname};
			  #print STDERR "$pthrid\t$go_gid\tPanther_Alternative_ID plus dbname\t$go_gid\|$dbname\t$goacc\t$gotype\n";
			  #$mapped_pthrid{$pthrid}++;
			  #push(@matched_ptherid, $pthrid);
			  &addAnnotDetails($pthrid, $goacc, $ev_code, $with, $ref, $date, $contrib_group);
			  &goToPthr($pthrid,$gotype,$goacc,$qualifier, $ev_code, $with, $ref, $date, $contrib_group);
		  }
		  
		  elsif (((exists $alterid_to_pthrid{$go_gid}{$tax}) && (defined $alterid_to_pthrid{$go_gid}{$tax}))){
		      #print MAT "$_\n";
			  my $pthrid = $alterid_to_pthrid{$go_gid}{$tax};
			  #print STDERR "$pthrid\t$go_gid\tPanther_Alternative_ID plus taxon_id\t$go_gid\|$tax\t$goacc\t$gotype\n";
			  #$mapped_pthrid{$pthrid}++;
			  #push(@matched_ptherid, $pthrid);
			  &addAnnotDetails($pthrid, $goacc, $ev_code, $with, $ref, $date, $contrib_group);
			  &goToPthr($pthrid,$gotype,$goacc,$qualifier, $ev_code, $with, $ref, $date, $contrib_group);
		  }
		  
		  elsif(((exists $go_id_to_pthrid{$gsym}{$dbname}) && (defined $go_id_to_pthrid{$gsym}{$dbname}))){
		      #print MAT "$_\n";
			  my $pthrid = $go_id_to_pthrid{$gsym}{$dbname};
			  #print STDERR "$pthrid\t$go_gid\tPanther_Middle_ID(match to gene symbol in fullgo) plus dbname\t$gsym\|$dbname\t$goacc\t$gotype\n";
			  
			  #$mapped_pthrid{$pthrid}++;
			  #push(@matched_ptherid, $pthrid);
			  &addAnnotDetails($pthrid, $goacc, $ev_code, $with, $ref, $date, $contrib_group);
			  &goToPthr($pthrid,$gotype,$goacc,$qualifier, $ev_code, $with, $ref, $date, $contrib_group);
		  }
		  
		  elsif(((exists $go_id_to_pthrid{$gsym}{$tax}) && (defined $go_id_to_pthrid{$gsym}{$tax}))){
		      #print MAT "$_\n";
			  my $pthrid = $go_id_to_pthrid{$gsym}{$tax};
			  #print STDERR "$pthrid\t$go_gid\tPanther_Middle_ID(match to gene symbol in fullgo) plus taxon_id\t$gsym\|$tax\t$goacc\t$gotype\n";
			  
			  #$mapped_pthrid{$pthrid}++;
			  #push(@matched_ptherid, $pthrid);
			  &addAnnotDetails($pthrid, $goacc, $ev_code, $with, $ref, $date, $contrib_group);
			  &goToPthr($pthrid,$gotype,$goacc,$qualifier, $ev_code, $with, $ref, $date, $contrib_group);
		  }
		  
		  elsif (((exists $alterid_to_pthrid{$gsym}{$dbname}) && (defined $alterid_to_pthrid{$gsym}{$dbname}))){
		      #print MAT "$_\n";
			  my $pthrid = $alterid_to_pthrid{$gsym}{$dbname};
			  #print STDERR "$pthrid\t$go_gid\tPanther_Alternative_ID(match to gene symbol in fullgo) plus dbname\t$gsym\|$dbname\t$goacc\t$gotype\n";
			  #$mapped_pthrid{$pthrid}++;
			  #push(@matched_ptherid, $pthrid);
			  &addAnnotDetails($pthrid, $goacc, $ev_code, $with, $ref, $date, $contrib_group);
			  &goToPthr($pthrid,$gotype,$goacc,$qualifier, $ev_code, $with, $ref, $date, $contrib_group);
		  }
		  
		  elsif (((exists $alterid_to_pthrid{$gsym}{$tax}) && (defined $alterid_to_pthrid{$gsym}{$tax}))){
		      #print MAT "$_\n";
			  my $pthrid = $alterid_to_pthrid{$gsym}{$tax};
			  #print STDERR "$pthrid\t$go_gid\tPanther_Alternative_ID(match to gene symbol in fullgo) plus taxon_id\t$gsym\|$tax\t$goacc\t$gotype\n";
			  #$mapped_pthrid{$pthrid}++;
			  #push(@matched_ptherid, $pthrid);
			  &addAnnotDetails($pthrid, $goacc, $ev_code, $with, $ref, $date, $contrib_group);
			  &goToPthr($pthrid,$gotype,$goacc,$qualifier, $ev_code, $with, $ref, $date, $contrib_group);
		  }
		  
		  
		  elsif (exists $gene_symbol_taxa_to_pthr{$gsym}{$tax} && defined $gene_symbol_taxa_to_pthr{$gsym}{$tax} ){
		      #print MAT "$_\n";
			  my $pthrid = $gene_symbol_taxa_to_pthr{$gsym}{$tax};
			  #print STDERR "$pthrid\t$go_gid\tPanther_Gene_Symbol(match to gene symbol in fullgo) plus taxon_id\t$gsym\|$tax\t$goacc\t$gotype\n";
			  #$mapped_pthrid{$pthrid}++;
			  #push(@matched_ptherid, $pthrid);
			  &addAnnotDetails($pthrid, $goacc, $ev_code, $with, $ref, $date, $contrib_group);
			  &goToPthr($pthrid,$gotype,$goacc,$qualifier, $ev_code, $with, $ref, $date, $contrib_group);
		  }
		  else {
		      print STDERR "$go_gid did not map to any PANTHER ID\n";
		      #print UMAT "$_\n";
			  
		   }
	}
    close(GAF);

}
print STDERR "Loaded GAF files\n";


for my $k (sort keys %gomfw) {
 
	 @{ $gomfw{$k} }=uniq(@{ $gomfw{$k} });
	 if(@{ $gomfw{$k} }){
		 for my $go_term (@{ $gomfw{$k} }){
		    # printf GOW "%s\t%s\n", $k, join "\t", @{ $go_term };
			my $term = @{ $go_term }[0];
			my $qual = @{ $go_term }[1];
			my $ev_code = @{ $go_term }[2];
			my $with = @{ $go_term }[3];
			my $ref = @{ $go_term }[4];
			my $date = @{ $go_term }[5];
			my $cgroup = @{ $go_term }[6];
			printf GOW "%s\t%s\t%s\t%s\t%s\t%s\t%s\n", $k, $term, $qual, $ev_code, $with, $ref, $cgroup;
			print FN2 "$k\t$golist{$term}\t$ev_code\t$with\t$ref\t$date\t$cgroup\n";
		 };
	 }
}
for my $j (sort keys %gobpw) {
	 @{ $gobpw{$j} }=uniq(@{ $gobpw{$j} });
	 if(@{ $gobpw{$j} }){
		 for my $go_term (@{ $gobpw{$j} }){
			# printf GOW "%s\t%s\n", $j, join "\t", @{ $go_term };
			my $term = @{ $go_term }[0];
			my $qual = @{ $go_term }[1];
			my $ev_code = @{ $go_term }[2];
			my $with = @{ $go_term }[3];
			my $ref = @{ $go_term }[4];
			my $date = @{ $go_term }[5];
			my $cgroup = @{ $go_term }[6];
			printf GOW "%s\t%s\t%s\t%s\t%s\t%s\t%s\n", $j, $term, $qual, $ev_code, $with, $ref, $cgroup;
			print FN1 "$j\t$golist{$term}\t$ev_code\t$with\t$ref\t$date\t$cgroup\n";
		 };
	 }
}
for my $l (sort keys %goccw) {
	@{ $goccw{$l} }=uniq(@{ $goccw{$l} });
	 if(@{ $goccw{$l} }){
		 for my $go_term (@{ $goccw{$l} }){
			# printf GOW "%s\t%s\n", $l, join "\t", @{ $go_term };
			my $term = @{ $go_term }[0];
			my $qual = @{ $go_term }[1];
			my $ev_code = @{ $go_term }[2];
			my $with = @{ $go_term }[3];
			my $ref = @{ $go_term }[4];
			my $date = @{ $go_term }[5];
			my $cgroup = @{ $go_term }[6];
			printf GOW "%s\t%s\t%s\t%s\t%s\t%s\t%s\n", $l, $term, $qual, $ev_code, $with, $ref, $cgroup;
			print FN3 "$l\t$golist{$term}\t$ev_code\t$with\t$ref\t$date\t$cgroup\n";
		 };
	 }
}
print STDERR "Did something with MF-BP-CC outputs.\n";
print STDERR "Job finished on ".ctime()."\n";

sub goToPthr{
    my ($pthrid,$gotype,$goacc,$qualifier, $ev_code, $with, $ref, $date, $cgroup)=@_;
	if($gotype eq 'molecular_function'){	
           push( @{$gomfw{$pthrid}}, [$goacc, $qualifier, $ev_code, $with, $ref, $date, $cgroup]);
		}
	  elsif($gotype eq 'biological_process'){
		
		   push( @{$gobpw{$pthrid}}, [$goacc, $qualifier, $ev_code, $with, $ref, $date, $cgroup] );
		}
	  elsif($gotype eq 'cellular_component'){
		
		   push( @{$goccw{$pthrid}}, [$goacc, $qualifier, $ev_code, $with, $ref, $date, $cgroup] );
		}
	  else {
		print STDERR "Could not assign go type to a matched go term\n";
	  }
}

sub addAnnotDetails{
	my ($gid, $goacc, $ev_code, $with, $xref, $date, $db) = @_;
	my $ref1=$with."\t".$xref."\t".$date."\t".$db;
	
	$refre{"$gid"."$goacc"."$ev_code"}=$ref1;
}

sub checkQualifier{
	my ($qual) = @_;

	@quals = split(/\|/, $qual);
	my @new_quals;
	for my $q (@quals){
		# Only pass through qualifiers if NOT or contributes_to or colocalizes_with.
		# So, drop gp2term relations. We may change this when we decide what PAINT should
		#  do with these.
		if ($q eq 'NOT' || $q eq 'contributes_to' || $q eq 'colocalizes_with'){
			push(@new_quals, $q);
		}
	}
	my $new_qual = join("\|", @new_quals);

	return $new_qual;
}
 
 sub usage {
    my $error = shift;

    print <<__EOT;

 

Usage:
example:    
perl fullGoMappingPthr.pl -f gaf_files/ -t pthr12_code_taxId.txt -i identifier.dat -g gene.dat -o go.obo  -w Pthr_GO.tsv -e log.txt




__EOT

  print "Error: $error\n\n" if ($error);

  exit(-1);
}
