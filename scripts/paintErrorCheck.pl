#!/usr/bin/perl

# use strict;

use LWP::Simple;



my $lib = $ARGV[0];
my $url = $ARGV[1];

# my $node = $ARGV[1];



# open ND, "$node";

# %leafNodes;

# while (<ND>){

# 	chomp;

# 	my ($an, $ptn, $type, @else) = split("\t");

#     next unless ($type =~ /LEAF/);

#     $leafNodes{$ptn}=1;

# }



opendir BK, "$lib/books";





foreach my $book (readdir BK){

	next unless $book =~ /^PTHR\d+$/;

	$new_url = $url;
	$new_url =~ s/book_var/$book/g;
	print $new_url;
	# my $content = get("http://paintcuration.usc.edu/webservices/family.jsp?searchValue=$book&searchType=SEARCH_TYPE_FAMILY_ANNOTATION_INFO") or die "no such luck\n";
	# my $content = get("http://panthercuratest.usc.edu/webservices/family.jsp?searchValue=$book&searchType=SEARCH_TYPE_AGG_FAMILY_ANNOTATION_INFO") or die "no such luck\n";
	my $content = get($new_url) or die "no such luck\n";

	

	print "$content\n"; 

}



