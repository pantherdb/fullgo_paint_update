#! /usr/local/bin/perl
use POSIX qw(strftime);

#####
#####
##
##  This script creates PAINT GAF files for GO.
##  The input files are generated from the postgres database
##    inputs:
##      -i property file with go and panther version.
##      -d for the data folder from library
##      -a paint_annotation (from database)
##      -q paint_annotation_qualifier (from database)
##      -g go_aggregate (from database)
##      -t TAIR10_TAIRlocusaccessionID_AGI_mapping.txt
##      -c evidence (from database)
##      -T organism_taxon
##      -G gene.dat in the DBload folder
##      -o output IBA gaf file folder
##
#####
#####

# get command-line arguments
use Getopt::Std;
getopts('o:i:a:q:g:n:N:G:b:C:t:u:c:T:e:s:vVh') || &usage();
&usage() if ($opt_h);         # -h for help
$outDir = $opt_o if ($opt_o);     # -o for (o)utput directory
$inFile = $opt_i if ($opt_i);     # -i for (i)Input profile file
# $data = $opt_d if ($opt_d);       # -d for the data folder from library
$node_dat = $opt_n if ($opt_n);       # -d for the data folder from library
$treeNodes_dir = $opt_N if ($opt_N);       # -d for the data folder from library
$annotation = $opt_a if ($opt_a); # -a for annotation file
$go_aggregate = $opt_g if ($opt_g); # -g for go_aggregate file
$qualifier = $opt_q if ($opt_q);  # -q for qualifier file
$tair = $opt_t if ($opt_t);       # -t for the TAIR ID lookup file
$araport = $opt_u if ($opt_u);    # -u for the UniProt-to-Araport ID lookup file
$evidence = $opt_c if ($opt_c);   # -c for evidence file
$taxon = $opt_T if ($opt_T);      # -T for the taxon file
$gene_dat = $opt_G if ($opt_G);   # -G for the gene.dat file in DB load folder
$gene_blacklist = $opt_b if ($opt_b);   # -b for the obsoleted UniProt ID blacklist file
$complex_termlist = $opt_C if ($opt_C);   # -C for the protein-containing complex descendants file
$gaf_version = $opt_s if ($opt_s); # -s for output GAF specification version 2.1 (default) or 2.2
$errFile = $opt_e if ($opt_e);    # -e for (e)rror file (redirect STDERR)
$verbose = 1 if ($opt_v);         # -v for (v)erbose (debug info to STDERR)
$verbose = 2 if ($opt_V);         # -V for (V)ery verbose (debug info STDERR)

###
### PUT YOUR CODE HERE
###

my %default_qualifiers = (F => 'enables', P => 'involved_in', C => 'is_active_in', complex => 'part_of');
if (!$gaf_version) {
    $gaf_version = '2.1';
}

my $go_version;
my $panther_version;
#############################
#  Parse the profile file
#############################

open (FH, $inFile) or die "Could not open file $inFile\n";
while (my $line = <FH>){
    chomp $line;
    my @array = split(/\t/, $line);
    if ($array[0] =~/^GO/){
        $go_version = $array[1];
    }else{
        $panther_version = $array[1];
    }
}
close (FH);

print STDERR "GO version is $go_version\n";
print STDERR "PANTHER version is $panther_version\n";

###############################
# Parse TAIR ID lookup file
###############################
my %tair;   # atg and locus ID lookup file.
open (TA, $tair) or die "Could not open file $tair\n";
while (my $line=<TA>){
    chomp $line;
    my ($locus, $agi)=split(/\t/, $line);
    $tair{$agi}=$locus;
}
close (TA);

###############################
# Parse Uniprot-to-Araport ID lookup file
###############################
my %araport;   # atg and locus ID lookup file.
open (AR, $araport) or die "Could not open file $araport\n";
while (my $line=<AR>){
    chomp $line;
    my ($uniprotid, $agi, $rest)=split(/\t/, $line);
    $araport{$uniprotid}=$agi;
}
close (AR);

#################################
# Parse the taxon file
#################################

my %taxon;
open (TA, $taxon) or die "Could not open file $taxon\n";
while (my $line=<TA>){
    chomp $line;
    
    my ($org, $sh_name, $id)=split(/;/, $line);
    $taxon{$sh_name}=$id;
}
close (TA);

###################################################
# Work on the node_paint.dat file.
# This is to generate the ptn to AN lookup hashes
###################################################

my $node = $node_dat;   # from PANTHER version.
my %ptn_an;
my %an_ptn;
open (FH, $node) or die "Could not open file $node\n";
#my $header=<FH>;
while (my $line=<FH>){
    chomp $line;
    my ($an, $ptn, $type, $event, @rest)=split(/\t/, $line);
        
    my $book=$an;
    $book=~s/\:AN\d+//;
    
    $ptn_an{$ptn}={$an};
    $an_ptn{$an}=$ptn;
}
close (FH);

###################################
# Parse treeNodes files
###################################

my $tree = $treeNodes_dir;
opendir (TREE, $tree);
my @files = readdir TREE;
close (TREE);
shift @files;
shift @files;

my %parent_child;
my %child_parent;
my %leaf;
my %id_lookup;  # the long ID to gene or protein ID lookup
my %node_taxon;   # the node to taxon hash;
my %leaf_ptn;

foreach my $file (@files){
    my $treeNode = "$tree/$file";
    my $book = $file;
    $book =~s/(PTHR\d+)\.\S+/$1/;
    
    open (FH, $treeNode);
    while (my $line=<FH>){
        chomp $line;
        my ($an, $type, $event, $ancestor, $parent_an, @rest)=split(/\t/, $line);
        my $node = "$book:$an";
        #  my $ptn = $an_ptn{$node};
        
        if (defined $taxon{$ancestor}){
            my $taxon = $taxon{$ancestor};
            $node_taxon{$node}=$taxon;
        }
        
        if ($parent_an){
            my $parent = "$book:$parent_an";
            $parent_child{$parent}{$node}=1;
            $child_parent{$node}=$parent;
        }
        
        my $foo;
        if ($type eq 'LEAF'){
            my $longId = $event;
            $leaf{$node}=$longId;
            
            my $ptn = $an_ptn{$node};
            $leaf_ptn{$longId}=$ptn;
            
            my ($org, $geneId, $proteinId) =split (/\|/, $longId);
            $geneId=~s/\=/\:/g;
            $proteinId=~s/\=/\:/g;
            
            my $shortId;   # the gene or protein ID used for GO.
            if ($geneId=~/^Gene|Ensembl/){
                $shortId=$proteinId;
            }else{
                if($geneId =~/FlyBase/){
                    $geneId=~s/FlyBase/FB/;
                    $shortId = $geneId;
                }elsif ($geneId =~/WormBase/){
                    $geneId=~s/WormBase/WB/;
                    $shortId = $geneId;
                }elsif ($geneId=~/^TAIR/ && !($geneId=~/^TAIR:locus:\d+/)){
                    $geneId=~s/^\w+\://;
                    if ($geneId eq 'locus'){
                        $proteinId=~s/^\w+\://;
                        if (defined $araport{$proteinId}){
                            $geneId = $araport{$proteinId};
                        }
                    }
                    if (defined $tair{$geneId}){
                        my $locus = $tair{$geneId};
                        $shortId="TAIR:locus:$locus";
                    }else{
                        print STDERR "TAIR ID $geneId has no mapped locus link ID.\n";
                        next;
                    }
                }elsif ($geneId=~/Araport/){
                    $geneId=~s/^\w+\://;
                    if (defined $tair{$geneId}){
                        my $locus = $tair{$geneId};
                        $shortId="TAIR:locus:$locus";
                    }else{
                        print STDERR "Araport ID $geneId has no mapped locus link ID.\n";
                        next;
                    }
                }elsif ($geneId=~/HGNC/){
                    $shortId=$proteinId;
                }elsif ($geneId=~/EcoGene/){
                    $shortId=$proteinId;
                }else{
                    $shortId = $geneId;
                }
            }
            #print "$shortId\n";
            $id_lookup{$longId}=$shortId;
        }
    }
    close (FH);
}

#################################
# Parse qualifier table
#################################

my %qualifier;
open (QA, $qualifier) or die "Could not open file $qualifier\n";
while (my $line = <QA>){
    chomp $line;
    my ($annotation_id, $qual)=split(/\;/, $line);
    if ($qual =~/CONTRIBUTES|COLOCALIZES/){
        $qual=~tr/[A-Z]/[a-z]/;
    }
    $qualifier{$annotation_id}{$qual}=1;  # Support multiple quals
}
close (QA);

##################################
# Parse go aggregate file
##################################

my %experimental_seqs;
my %exp_qualifier;
open (GA, $go_aggregate) or die "Could not open file $go_aggregate\n";
while (my $line=<GA>){
    chomp $line;
    my ($annotation_id, $an, $go, $type, $evidence_id, $evidence, $confidence, $exp_qual, $rest)=split(/\;/, $line);
    next unless ($confidence=~/IDA|EXP|IMP|IPI|IGI|IEP/);
    if ($exp_qual =~/CONTRIBUTES|COLOCALIZES/){
        $exp_qual=~tr/[A-Z]/[a-z]/;
    }
    $experimental_seqs{$annotation_id}=$an;
    $longId = $leaf{$an};
    $exp_qualifier{$longId}{$go}{$evidence_id}{$exp_qual}=1;  # Need to track by evidence_id
}

close (GA);

#########################################
# Parse the gene_dat file
#########################################

my %gene_symbol;
my %gene_def;
open (GD, $gene_dat) or die "Could not open file $gene_dat\n";
while (my $line=<GD>){
    chomp $line;
    my ($longId, $def, $symbol, $id)=split(/\t/, $line);
    #  $longId =~s/\=/\:/g;
    if ($symbol){
        $gene_symbol{$longId}=$symbol;
    }
    $gene_def{$longId}=$def;
}

close (GD);

#########################################
# Parse the gene_blacklist file
#########################################

my %blacklisted_genes;
open (BL, $gene_blacklist);
while (my $line=<BL>){
    chomp $line;
    $blacklisted_genes{$line}=1;
}
close (BL);

#########################################
# Parse the complex_termlist file
#########################################

my %complex_terms;
open (CL, $complex_termlist);
while (my $line=<CL>){
    chomp $line;
    $complex_terms{$line}=1;
}
close (CL);

##########################################
# Parse annotation file.
##########################################

my %annotation;
open (PA, $annotation) or die "Could not open file $annotation\n";
while (my $line=<PA>){
    chomp $line;
    
    my ($annotation_id, $an, $ptn, $go, $go_name, $type, $date)=split(/\;/, $line);
    $annotation{$annotation_id}=$line;
    
}
close (PA);

# create node and leaf gene hash

my %node_genes;
foreach my $id (keys %annotation){
    my $line=$annotation{$id};
    
    my ($annotation_id, $an, $ptn, $go, $go_name, $type, $date)=split(/\;/, $line);
    my %allGenes = &findGeneInPTN($an, \%parent_child, \%leaf); # all gene in current book.
    foreach my $gene (keys %allGenes){
        $node_genes{$ptn}{$gene}=1;
    }
}

###########################################
# Parse evidence table
###########################################

my %with;
my %nots;
my %confidence_codes;
open (EV, $evidence) or die "Could not open file $evidence\n";
while (my $line=<EV>){
    chomp $line;
    my ($annotation_id, $evidence, $type, $confidence_code)=split(/\;/, $line);
    
    $confidence_codes{$annotation_id}=$confidence_code;
    if ($type=~/PAINT\_EXP/){
        if (defined $experimental_seqs{$evidence}){
            my $an = $experimental_seqs{$evidence};
            my $longId;
            if (defined $leaf{$an}){
                $longId = $leaf{$an};
                my $id = $id_lookup{$longId};
                $with{$annotation_id}{$id}=1;
                
            }else{
                print STDERR "Can't find long id for $an.\n";
            }
        }else{
            print STDERR "Annotation ID $annotation_id has $evidence as experimental evidence that can't be found in go_aggregate table.\n";
        }

    }elsif ($type=~/PAINT\_ANCESTOR/){
        if (defined $annotation{$evidence}){
            my $line=$annotation{$evidence};  # the ancestor node
            my ($id, $an, $ptn, $go, $go_name, $type)=split(/\;/, $line);
            $with{$annotation_id}{"PANTHER:$ptn"}=1;
            
            #  my $line_a = $annotation{$annotation_id};  # the current node.
            #  my ($id_a, $an_a, $ptn_a, $go_a, $go_name_a, $type_a)=split(/\t/, $line_a);
            $nots{$evidence}{$annotation_id}=$confidence_code;
        }else{
            print STDERR "Annotation ID $annotation_id has $evidence as ancestor node evidence that can't be found in annotation table.\n";
        }
    }else{
        print STDERR "$type\n";
    }
}
close (EV);

###########################################
# print ancestor annotation (IBD) gaf files
###########################################

my %IBAs;

print "\!gaf-version: 2.1\n";
print "\!Created on " . localtime . ".\n";
print "\!PANTHER version: $panther_version.\n";
print "\!GO version: $go_version.\n";
foreach my $annotation_id (keys %annotation){
    my $line = $annotation{$annotation_id};
    
    my ($annotation_id, $an, $ptn, $go, $go_name, $type, $date)=split(/\;/, $line);
    
    $date=~s/(\d+\-\d+\-\d+)\s\S+/$1/;
    $date=~s/\-//g;
    
    my $ontology;
    if ($type=~/cellular/){
        $ontology = 'C';
    }elsif($type=~/molecular/){
        $ontology = 'F';
    }else{
        $ontology = 'P';
    }
    
    my $qual = '';
    if (defined $qualifier{$annotation_id}){
        # Get full "|"-separated format
        $qual = qualOutput(keys %{$qualifier{$annotation_id}});
    }
    my @quals = split(/\|/, $qual);  # Used in comparing PAINT qualifiers against experimental qualifiers
    if (!@quals){
        @quals = ('');
    }
    
    my $db_ref = 'PMID:21873635';
    
    my $with;
    if (defined $with{$annotation_id}){
        my @withs = keys %{$with{$annotation_id}};
        $with = join ("\|", @withs);
    }else{
        print STDERR "Annotation ID $annotation_id has no evidence support in the 'with' column.\n";
    }
    
    my $fam = $an;
    $fam=~s/PTHR(\d+)\:AN\d+/$1/;
    
    my $confidence_code;
    if (defined $confidence_codes{$annotation_id}){
        $confidence_code = $confidence_codes{$annotation_id};
    }else{
        print STDERR "Annotation ID $annotation_id has no confidence conde.\n";
    }
    
    next if (!$with || !$confidence_code);
    
    my $taxon;
    if (defined $node_taxon{$an}){
        $taxon = $node_taxon{$an};
    }else{
        print STDERR "$an has no taxon ID.\n";
    }
    
    # print "PANTHER\t$ptn\t$ptn\t$qual\t$go\t$db_ref\t$confidence_code\t$with\t$ontology\t\t\tprotein\ttaxon:$taxon\t$date\tGO_Central\t\t\n";
    my $msg = "PANTHER\t$ptn\t$ptn\t$qual\t$go\t$db_ref\t$confidence_code\t$with\t$ontology\t\t\tprotein\ttaxon:$taxon\t$date\tGO_Central\t\t\n";
    $msg =~ s/\r//;
    print $msg;

    # next unless ($qual eq 'NOT');
    
    ###################################################
    # print IBAs.
    # print individual file for the following genomes
    # -mgi
    # -fb
    # -ecocyc
    # -tair
    # -chicken
    # -human
    # -rgd
    # -zfin
    # -pombase
    # -dictyBase
    # -cgd
    # -wb
    # -sgd
    #
    # print the rest as 'others'
    #####################################################
    
    next if ($confidence_code =~/IRD|TCV/);
    
    # First, create a hash of all genes under an annotated node.
    
    my %not_genes;  # leaf of the descendant nodes that have IKR or IRD annotations.
    if (defined $nots{$annotation_id}){
        foreach $not_annotation_id (keys %{$nots{$annotation_id}}){
            my $confidence_code = $nots{$annotation_id}{$not_annotation_id};
            my $not_line;
            if (defined $annotation{$not_annotation_id}){
                $not_line = $annotation{$not_annotation_id};
            }else{
                print STDERR "Annotation ID $not_annotation_id is used as an evidence for a $confidence_code annotation of $annotation_id, but can't be found in the annotation table.\n";
            }
            my ($annotation_id_n, $an_n, $ptn_n, $go_n, $go_name_n, $type_n)=split(/\;/, $not_line);
            
            if (defined $node_genes{$ptn_n}){
                foreach my $gene (keys %{$node_genes{$ptn_n}}){
                    if ($confidence_code =~/IKR/){
                        $not_genes{$gene}=1;
                        
                        
                    }elsif ($confidence_code =~/IRD/){
                        $not_genes{$gene}=1;
                    }
                }
            }elsif (defined $leaf{$an_n}){
                my $leaf_gene = $leaf{$an_n};
                if ($confidence_code =~/IKR|IRD/){
                    $not_genes{$leaf_gene}=1;
                }
            }else{
                print STDERR "No leaf genes found for $ptn_n.\n";
            }
        }
    }
    if (defined $node_genes{$ptn}){
        foreach my $gene (keys %{$node_genes{$ptn}}){
            # my %positive_quals = (''=>1, 'colocalizes_with'=>1, 'contributes_to'=>1);  # no qualifier, colocalizes_with, and contributes_to are considered positive
            # my %negative_quals = ('NOT'=>1);  # NOT is negative
            my $qual_supported=0;
            if (defined $exp_qualifier{$gene} && defined $exp_qualifier{$gene}{$go}){
                foreach my $ev_id (keys %{$exp_qualifier{$gene}{$go}}){
                    foreach my $exp_qual (keys %{$exp_qualifier{$gene}{$go}{$ev_id}}){
                        foreach my $q (@quals){
                            # exp_qual will be either NOT, colocalizes_with, contributes_to, or ''
                            if ($q eq $exp_qual) {
                                # IBA qualifier is valid if agreement w/ any same-term experimental annotation qualifier
                                $qual_supported=1;
                            }
                        }
                    }
                }
            } else {
                # No same-term experimental annotations that could possibly contradict qualifier? Then it's good
                $qual_supported=1;
            }
            if (!$qual_supported) {
                $not_genes{$gene}=1;
            }
            next if (defined $not_genes{$gene});
            
            my $qual_output = $qual;
            if ($gaf_version eq '2.2') {
                my $default_qualifier;
                if ($ontology eq 'C' && defined $complex_terms{$go}) {
                    $default_qualifier = $default_qualifiers{'complex'};
                } else {
                    $default_qualifier = $default_qualifiers{$ontology};
                }
                # Add default qualifier if blank or "NOT"-only
                if ($qual eq 'NOT') {
                    $qual_output = "NOT|$default_qualifier";
                } elsif ($qual eq '') {
                    $qual_output = $default_qualifier;
                }
            }

            my $short_id;
            if (defined $id_lookup{$gene}){
                $short_id = $id_lookup{$gene};
            }else{
                print STDERR "$gene -- not short IDs found in the hash.\n";
            }
            
            my $db;
            if ($short_id=~/(^\w+)\:\S+/){
                $db = $1;
            }
            $short_id =~s/^\w+\://;
            
            my $symbol;
            if (defined $gene_symbol{$gene}){
                $symbol = $gene_symbol{$gene};
            }else{
                $symbol = $short_id;
                print STDERR "$gene -- no gene symbol found.\n";
            }
            
            my $def;
            if (defined $gene_def{$gene}){
                $def = $gene_def{$gene};
            }else{
                print STDERR "$gene -- no gene definition found.\n";
            }
            
            my ($org, $geneId, $uniprot) = split(/\|/, $gene);
            my $gene_taxon;
            if (defined $taxon{$org}){
                $gene_taxon=$taxon{$org};
            }else{
                print STDERR "Gene organism $org has no taxon ID found.\n";
            }
            
            $uniprot =~s/\=/\:/g;

            # Skip IBA for UniProt IDs that have since been obsoleted / missing from UniProt GPI
            my ($prefix, $uniprot_id) = split(/\:/, $uniprot);
            if (defined $blacklisted_genes{$uniprot_id}){
                print STDERR "Skipping - obsolete ID missing from latest uniprot_protein.gpi\ttaxon\:$gene_taxon\t$uniprot\n";
                next;
            }
            
            my $leaf_ptn;
            if (defined $leaf_ptn{$gene}){
                $leaf_ptn=$leaf_ptn{$gene};
            }else{
                print STDERR "$gene has no ptn id found.\n";
            }
            next unless ($db);
            next unless ($short_id);
            my $foo = "$db\t$short_id\t$symbol\t$qual_output\t$go\t$db_ref\tIBA\tPANTHER\:$ptn\|$with\t$ontology\t$def\t$uniprot\|$leaf_ptn\tprotein\ttaxon\:$gene_taxon\t$date\tGO_Central\t\t";
            
            my $file_type;
            if ($org eq 'MOUSE'){
                $file_type = "mgi";
            }elsif ($org eq 'HUMAN'){
                $file_type = "human";
            }elsif ($org eq 'RAT'){
                $file_type = "rgd";
            }elsif ($org eq 'DROME'){
                $file_type = "fb";
            }elsif ($org eq 'ARATH'){
                $file_type = "tair";
            }elsif ($org eq 'CAEEL'){
                $file_type = "wb";
            }elsif ($org eq 'CHiCK'){
                $file_type = "chicken";
            }elsif ($org eq 'ECOLI'){
                $file_type = "ecocyc";
            }elsif ($org eq 'YEAST'){
                $file_type = "sgd";
            }elsif ($org eq 'DICDI'){
                $file_type = "dictyBase";
            }elsif ($org eq 'SCHPO'){
                $file_type = "pombase";
            }elsif ($org eq 'DANRE'){
                $file_type = "zfin";
            }elsif ($org eq 'CANAL'){
                $file_type = "cgd";
            }elsif ($org eq 'CHICK'){
                $file_type = "chicken";
            }elsif ($org eq 'XENTR'){
                $file_type = "xenbase";
            }else{
                $file_type = "other";
            }

            $IBAs{$file_type}{$foo}=1;
        }
    }
}

foreach my $type (keys %IBAs){
    my $outFile = "gene_association.paint_$type.gaf";
    my $datestring = strftime "%F", localtime;

    open (OUT, ">$outDir/$outFile");
    print OUT "\!gaf-version: $gaf_version\n";
    print OUT "\!Created on " . localtime . ".\n";
    print OUT "\!generated-by: PANTHER\n";
    print OUT "\!date-generated: $datestring\n";
    print OUT "\!PANTHER version: $panther_version.\n";
    print OUT "\!GO version: $go_version.\n";
        foreach my $line (keys %{$IBAs{$type}}){
            # print OUT "$line\n";
            my $msg = "$line\n";
            $msg =~ s/\r//;
            print OUT "$msg";
        }
    close (OUT);
    
}

#########################################
# subroutines
#########################################

sub findGeneInPTN{
    my ($an, $parent_child_href, $leaf_href)=@_;
    
    my %children;
    my %leaf;
    if (defined $parent_child_href->{$an}){
        my @array = keys %{$parent_child_href->{$an}};
        
        my @parents = @array;
        
        while (@parents){
            my @childs;
            foreach my $parent (@parents){
                $children{$parent}=1;
                if (defined $leaf_href->{$parent}){
                    my $longId = $leaf_href->{$parent};
                    $leaf{$longId}=1;
                }else{
                    
                    if (defined $parent_child_href->{$parent}){
                        my @a = keys %{$parent_child_href->{$parent}};
                        push (@childs, @a);
                    }else{
                        
                        print STDERR "$parent is not a leaf but no child is found.\n";
                    }
                }
            }
            @parents = @childs;
        }
    }
    return %leaf;
    
}

sub qualOutput{
    my $negated;
    my @quals;
    foreach my $q (@_){
        if ($q eq "NOT"){
            $negated=1;
        }else{
            push (@quals, $q);
        }
    }
    if ($negated){
        unshift (@quals, "NOT");
    }
    my $qual_output = join ("\|", @quals);
    return $qual_output;
}

