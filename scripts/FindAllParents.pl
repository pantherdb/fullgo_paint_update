#!/usr/bin/perl


#############################################################################
# Program       : FindAllParents.pl                               #
# Author        : Sagar Poudel                            					#
# Date          : 10.20.2012                                                #
#                                                                           #
# This program finds all the parent nodes of a child. This program can finds#
# All parents term for GO terms in Geneontology. Below Code is			    #
# Modified for finding all parents of PantherNode                			# 
# Inputfile: List of Parent-Child node                                      #
# Outputfile: List of Parent of a Child node  
#ex: perl FindAllParents.pl goparentchild.tsv AllParentsofGOTerms.txt       #
#############################################################################


 
#use warnings;
#use strict;
#use Data::Dumper;
BEGIN { $ENV{LIST_MOREUTILS_PP}=1; }
use Carp;
use List::Util qw(first max maxstr);
use List::MoreUtils qw(uniq);
use Array::Utils qw(:all);

#use Data::Dump::Streamer;
#use DDS;
#open file to read
my $fName = $ARGV[0];
my $output = $ARGV[1];
open(GOS, $fName) or die $!;
open(OUT, ">$output") or die $!;

my %pthr;
my %ptpar;
while(<GOS>)
	{
	next unless $_ =~ /^GO:/;
	my $line1 = $_;
	chomp($line1);
	my($go11,$go12) = split('\t');
	chomp($go11,$go12);
	#inserting data into array of hash
	#testing for all children of goterm
	push( @{$ptpar{$go12}}, $go11 );
	#$pthr{$go11}= $go12;
	}

#$Data::TreeDumper::Useascii = 0 ;
#$Data::TreeDumper::Maxdepth = 2 ;	
my @stack = ();

my %hway=();
foreach my $pgsymbol (sort keys %ptpar)	{
	chomp($pgsymbol);
	
my @myway=();
						
# add begin to stack
push(@stack, { node => $pgsymbol, way => [$pgsymbol] });

while (@stack > 0) {

    my $node = pop(@stack);

    # way
    my $way = $node->{way};

    # complete way Print with particuler condition
   # if ($node->{node} eq 'GO:0003674' or $node->{node} eq 'GO:0005575' or $node->{node} eq 'GO:0008150') {
      #  print Dumper($node->{way});
   #}

    # add next nodes
    my $nextArr = $ptpar{$node->{node}};

    for my $nextNod (@$nextArr) {
        # add way
        my @tmpWay = @$way;
        push(@tmpWay, $nextNod);

        # add to stack
        push(@stack, { node => $nextNod, way => \@tmpWay });
    }
	#Collecting all results in array
	
		@myway= @{$node->{way}};
	
}
#for each array(for a route)
#@myway=uniq @myway;
for(my $i=0;$i<@myway;$i++){
my $le=$myway[$i];

$le=~ y/['"(),;<>]//d;
$le=~ s/(^\s+|\s+$)//g;
print OUT $pgsymbol,"\t",$le,"\n";
}

}
close(GOS);
close(GOSOUT);
