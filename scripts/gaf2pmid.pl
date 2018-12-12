#!/usr/bin/perl

#use LWP 5.64;
#use LWP::Simple;
use utf8;
use Text::Unidecode;

use Getopt::Std;
getopts('g:e');
my $gaf_dir = $opt_g if ($opt_g);       # -g for directory containing gaf files

my $browser = LWP::UserAgent->new;
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
	print "$id\n";
}