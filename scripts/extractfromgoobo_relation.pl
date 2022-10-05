#!/usr/bin/perl 
#use strict;

use Getopt::Std;
getopts('h:i:o:Ie:v:V') || &usage();
&usage() if ($opt_h);          # -h for (h)elp
$input = $opt_i if ($opt_i);   # -i for (i)NPUT File
$output = $opt_o if ($opt_o);  # -o for (o)utput
$isaOnly = 1 if ($opt_I);      # -I for Extract (I)s_a relations only
$errFile = $opt_e if ($opt_e); # -e for (e)rror file (redirect STDERR)
$verbose = 1 if ($opt_v);      # -v for (v)erbose (debug info to STDERR)
$verbose = 2 if ($opt_V);      # -V for (V)ery verbose (debug info to STDERR)



open(GO, $input) or die $!;
open(OUT, ">$output") or die $!;

print OUT "Parent\tChild\n";
local $/="[Term]";




while (my $record=<GO>){
    my @alt_id;
	my $isa;
    my $isa1;
	chomp($_);
	my @lines=split(/\n/, $record);
	my $gid=(split(/id:/, $lines[1]))[1];
	$gid =~ s/^\s+|\s+$//g;
	for my $line (@lines) {
   # next if ($line =~ m/def:/);
		if ($line =~ /^is_a:/) {
			$isa=(split(/\s+/, $line))[1];
			$isa =~ s/^\s+|\s+$//g;
			print OUT "$isa\t$gid\n" if $isa =~ /^GO:/;
		}
		if (!$isaOnly && $line =~ /^relationship: part_of/) {
			$isa1=(split(/!/, $line))[0];
			$isa1 =~ s/relationship: part_of //g;
			$isa1 =~ s/^\s+|\s+$//g;
			print OUT "$isa1\t$gid\n" if $isa1 =~ /^GO:/;
		}
		
		if ($line =~ /^alt_id:/) {
	         push (@alt_id, (split(/alt_id:/, $line))[1]);
	    }
  
   }
   for my $alt_id (@alt_id){
	   $alt_id=~ s/^\s+|\s+$//g;
	   print OUT "$isa\t$alt_id\n" if $isa =~ /^GO:/;
	   print OUT "$isa1\t$alt_id\n" if $isa1 =~ /^GO:/;
   }

	
}
	
close(GO, OUT);
sub usage {
    my $error = shift;

    print <<__EOT;

extractfromobo_relation.pl - a program to extract parent-child relationship information from go.obo file

Usage:
    extractfromobo_relation.pl -i input data file name (go.obo) -o output file name (goparentchild.tsv)

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
