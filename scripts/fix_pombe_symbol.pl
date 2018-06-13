#! /usr/local/bin/perl

#####
#####
##
##  This script fixes the PAINT GAF files for pombe by updating the gene symbol.
##  This is a temporary fix.
##    inputs:
##      -i for input GAF file
##      -p for pombe id file
##
#####
#####

# get command-line arguments
use Getopt::Std;
getopts('o:i:p:d:e:vVh') || &usage();
&usage() if ($opt_h);         # -h for help
$outDir = $opt_o if ($opt_o);     # -o for (o)utput directory
$inFile = $opt_i if ($opt_i);     # -i for (i)Input gaf file
$pombe = $opt_p if ($opt_p);      # -p for the pombe lookup file
$desc_f = $opt_d if ($opt_d);       # -d for the description lookup file
$errFile = $opt_e if ($opt_e);    # -e for (e)rror file (redirect STDERR)
$verbose = 1 if ($opt_v);         # -v for (v)erbose (debug info to STDERR)
$verbose = 2 if ($opt_V);         # -V for (V)ery verbose (debug info STDERR)

my %hash;
open (PB, $pombe);
while (my $line=<PB>){
    chomp $line;
    my ($id, $symbol, $rest)=split(/\t/, $line);
    next unless ($symbol);
    $hash{$id}=$symbol;
    #print "$symbol\n";
}
close (PB);

my %d_hash;
open (DB, $desc_f);
while (my $line=<DB>){
    chomp $line;
    my @product_array=split(/\t/, $line);
    my $id=$product_array[0];
    my $desc=$product_array[-1];
    next unless ($desc);
    $d_hash{$id}=$desc;
    #print "$desc\n";
}
close (PB);

my $print_out = 1; # Handy on/off switch
my %update;
my %hash1;
my $line1 = "";
open (FH, $inFile);
while (my $line=<FH>){
    chomp $line;
    unless ($line=~/^PomBase/){
        print "$line\n" if $print_out;
        next;
    } else{
        my @array = split(/\t/, $line);
    
        my $id = $array[1];
        $hash1{$id}=1;
        if (defined $hash{$id}){
            if ($array[2] eq $hash{$id}){
                $update{'no change'}{$id}=1;
                print "$line\n" if $print_out;
            }else{
                if ($array[2] =~/SP/){  # symbol uses the SP ID
                    $update{'update_SP'}{$id}=1;
                }else{         # It is a gene symbol that is different from the one in the lookup file.
                    $update{'update'}{$id}=1;
                }
                $array[2]=$hash{$id};
                $array[9]=$d_hash{$id};
                $line1=join("\t", @array);
                #print "$line\n";
                print "$line1\n" if $print_out;
            }
        }else{
            if ($array[2] =~/SP/){   # SP id is used as symbol
                $update{'no_update_SP'}{$id}=1;
            }else{
                $update{'no_update'}{$id}=1;
                # print "$line\n";
            }
            $array[2]=$id;
            $array[9]=$d_hash{$id};
            $line1=join("\t", @array);
            print "$line1\n" if $print_out;
            #print "$array[2]\n";
        }
    }
}

my $totalcount = keys (%hash1);
my $count = keys (%{$update{'no change'}});
my $count_update_SP =  keys (%{$update{'update_SP'}});
my $count_update =  keys (%{$update{'update'}});
my $count_no_update = keys (%{$update{'no_update'}});
my $count_no_update_SP =  keys (%{$update{'no_update_SP'}});

# print "$totalcount\tTotal genes in the GAF file\n";
# print "$count\tCorrect gene symbol\n";
# print "$count_update_SP\tGene accessions updated to symbols\n";
# print "$count_update\tSymbols updated to new symbols\n";
# print "$count_no_update_SP\tNot in allName file (with gene accession in the symbol column\n";
# print "$count_no_update\tNot in allName file (with symbol in the symbol column\n";

close (FH);
