#!/usr/bin/perl-w 
#use strict;

my %pthr;
my %pgos;
my %gopar;
my %goname;
my %evi;
my %wevi;

my %golist;

my $dir = $ARGV[0];

#open REF, "<$dir/withRefValuesfrom_gene_association" or die $!;
open CP, "<$dir/FinalChildParent-Hierarchy.dat" or die $!;
open GONM, "<$dir/Pthr_GO.tsv" or die $!;
open GO, "<$dir/inputforGOClassification.tsv" or die $!;
open EC, "<$dir/../scripts/Paint_Evidence_Codes" or die $!;
# open GAF, "<$dir/goa_uniprot_gcrp.gaf" or die $!;
opendir(GAF, "$dir/gaf_files") or die $!;
#open CP, "<child-parents.txt" or die $!;
open FN1, ">$dir/GOWithHierarchy-BP.dat" or die $!;
open FN2, ">$dir/GOWithHierarchy-MF.dat" or die $!;
open FN3, ">$dir/GOWithHierarchy-CC.dat" or die $!;
print FN1 "SequenceID\tGOHierarchy\tEvidenceCode\tWith\tReference\tDate\tDB\n";
print FN2 "SequenceID\tGOHierarchy\tEvidenceCode\tWith\tReference\tDate\tDB\n";
print FN3 "SequenceID\tGOHierarchy\tEvidenceCode\tWith\tReference\tDate\tDB\n";

my %go;
while (my $record=<GO>){
    chomp $record;
	my ($gid,$name,$ttype,$def,$obsolete_date,$replace_term) = split(/\t/, $record);
	if($ttype eq '14'){
		 $ttype='MF';
		 }
	elsif($ttype eq '12'){
		 $ttype='BP';
		 }
	elsif($ttype eq '13'){
		$ttype='CC';
		 }
	$go{$gid}=$ttype;
	#print "$gid\t$ttype\n";
}
close(GO);

while (<CP>) 
	{
	chomp($_);
	my ($child,$parents) = split('\t');
	chomp($child,$parents);
	$golist{$child}=$parents;
    #print "$child\t$parents\n";
	}
close(CP);	
	
my %evCode;
while (<EC>){
    chomp;
	$_ =~ s/^\s+|\s+$//g;
	$evCode{$_} = 1;
}
close(EC);
#close(CP);
my %gevi;
my %refre;
for my $gaf (readdir GAF) {
	next if $file =~ /^\.\.?$/;
	print "working on $gaf\n";
	open (GAF_LINE, "$dir/gaf_files/$gaf");
	print STDERR "Parsing file: $gaf\n";
	while (<GAF_LINE>){
		next if /^!/;
		chomp($_);
		my ($db1,$gid,$sym,$qa,$goacc,$xref,$ev_code,$with,$type,$a1,$a2,$a3,$a4,$date,$db,$a5,$a6) = split('\t');
		$ev_code =~ s/^\s+|\s+$//g;
		next unless (exists $evCode{$ev_code});
		chomp($gid,$with,$xref,$ev_code,$date,$db);
		$gid =~ s/^\s+|\s+$//g;
		$with =~ s/^\s+|\s+$//g;
		$xref =~ s/^\s+|\s+$//g;
		$ev_code =~ s/^\s+|\s+$//g;
		$with =~ s/^\s+|\s+$//g;
		$date =~ s/^\s+|\s+$//g;
		$db =~ s/^\s+|\s+$//g;
		
		my $ref1=$with."\t".$xref."\t".$date."\t".$db;
		#print "$gid\t$goacc\t$ev_code\t$ref1\n";
		$refre{"$gid"."$goacc"."$ev_code"}=$ref1;
		
	} 
	close(GAF);
}

while (<GONM>) 
	 {
	 chomp($_);
	 my ($gene_ext_acc,$goacc, $qualifier, $ev_code, $with, $ref) = split('\t');
	 chomp($gene_ext_acc,$goacc, $qualifier, $ev_code, $with, $ref);
	$gene_ext_acc=~ s/^\s+|\s+$//g;
	$goacc=~ s/^\s+|\s+$//g;
	$ev_code=~ s/^\s+|\s+$//g;
	my ($u1,$u2,$u3) = split('=',$gene_ext_acc);
	chomp($u1,$u2,$u3);
	if($gene_ext_acc =~ /MGI\=MGI/){
		my $pr=(split('=', $gene_ext_acc))[-1];
		$u3=$pr;
		#print " pr is $pr \t u3 is $u3\n";

		}

	$u3 =~ s/^\s+|\s+$//g;
	 if(exists $golist{$goacc}){
		$first=$goacc;
		if ($go{$goacc} eq 'BP'){
		 print FN1 "$gene_ext_acc\t$golist{$goacc}\t$ev_code\t".$refre{"$u3"."$goacc"."$ev_code"}."\n";
		 }elsif ($go{$goacc} eq 'MF'){
		   print FN2 "$gene_ext_acc\t$golist{$goacc}\t$ev_code\t".$refre{"$u3"."$goacc"."$ev_code"}."\n";
		 }elsif ($go{$goacc} eq 'CC'){
		   print FN3 "$gene_ext_acc\t$golist{$goacc}\t$ev_code\t".$refre{"$u3"."$goacc"."$ev_code"}."\n";
		 }
		
	 }
	
	 
	 }
 close(GONM,FN1, FN2, FN3);
