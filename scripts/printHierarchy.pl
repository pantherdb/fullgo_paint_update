#!/usr/bin/perl 
#use strict;
BEGIN { $ENV{LIST_MOREUTILS_PP}=1; }
use Carp;
use List::MoreUtils qw(uniq);

my $input = $ARGV[0];
my $output = $ARGV[1];
open(CP, $input) or die $!;
open(OUT, ">$output") or die $!;

#open CP, "<AllParentsofGOTerms.txt" or die $!;

#open FN, ">Finalchildparent-hierarchy.dat" or die $!;
my %golist;
while (<CP>) 
	{
	chomp($_);
	my ($child,$parents) = split('\t');
	chomp($child,$parents);
	push( @{$golist{$child}},$parents);
  #push( @{$gomf{$pthr{$gid}}}, $insert );  
	}
	
for my $k (sort keys %golist) {
 
 @{ $golist{$k} }=uniq(@{ $golist{$k} });
 if(@{ $golist{$k} }){
 printf OUT "%s\t%s\n", $k, join '>', @{ $golist{$k} };
 }}