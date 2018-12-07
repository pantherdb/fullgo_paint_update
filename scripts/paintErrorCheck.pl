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



# opendir BK, "$lib/books";
open (BK, $lib);
while (my $book = <BK>){
    chomp $book;




# foreach my $book (readdir BK){

	next unless $book =~ /^PTHR\d+$/;

	$new_url = $url;
	$new_url =~ s/book_var/$book/g;
	# my $content = get("http://paintcuration.usc.edu/webservices/family.jsp?searchValue=$book&searchType=SEARCH_TYPE_FAMILY_ANNOTATION_INFO") or die "no such luck\n";
	# my $content = get("http://panthercuratest.usc.edu/webservices/family.jsp?searchValue=$book&searchType=SEARCH_TYPE_AGG_FAMILY_ANNOTATION_INFO") or die "no such luck\n";
	my $content = undef;
	my $attempt_count = 0;
	while (!defined $content){
		$content = get($new_url);
		if (!defined $content){
			# Stretch this out
			sleep(2);
		}
		$attempt_count++;
		if ($attempt_count eq 10){
			die "no such luck\n";
		}
	}

	

	print "$content\n"; 

}
close (BK);


