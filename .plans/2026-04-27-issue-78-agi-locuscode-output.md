# Issue #78: Output AGI_LocusCode IDs in TAIR/Arabidopsis IBA GAFs — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the legacy `TAIR:locus:NNNNN` short IDs emitted for Arabidopsis leaves in PAINT IBA GAFs with `AGI_LocusCode:ATxGNNNNN` IDs, sourced from a single new lookup file `resources/AGI_LocusCode_UniProt_19.gene2acc`.

**Architecture:** Add two small Perl subs (`parse_agi_lookup_file`, `lookup_agi`) **inline at the top of `scripts/createGAF.pl`**. Replace the existing TAIR + Araport hash-building blocks and the two ARATH-specific branches in the leaf-parsing loop with a single call to `lookup_agi`. Output filenames stay `gene_association.paint_tair.gaf` (TAIR is still the curating group); only the IDs inside change. Makefile and `createGAF.sh` / `createGAF_uniprot.sh` collapse the `-t TAIR_MAP` + `-u ARAPORT_MAP` flags into a single `-t AGI_MAP`. Delete the orphaned `scripts/createGAF_human_exp_references.pl` since its logic was already ported into `createGAF.pl`.

**Tech Stack:** Perl 5 (existing scripts), Bash (wrapper scripts), GNU Make.

---

## File Structure

**Modify:**
- `scripts/createGAF.pl` — add the two new subs near the top; replace the two `-t` / `-u` parsing blocks (lines ~37–106) with one `parse_agi_lookup_file` call; replace the ARATH branches in leaf parsing (lines ~249–272) with a `lookup_agi` call; drop `-u` from `getopts`.
- `Makefile` — replace `TAIR_MAP` and `ARAPORT_MAP` exports with one `AGI_MAP` export pointing at `resources/AGI_LocusCode_UniProt_19.gene2acc` (lines 94–97).
- `scripts/createGAF.sh` — pass `-t $AGI_MAP`; drop `-u $ARAPORT_MAP`.
- `scripts/createGAF_uniprot.sh` — same change.

**Delete:**
- `scripts/createGAF_human_exp_references.pl` — orphaned (no Makefile recipe or shell wrapper invokes it); logic already ported to `createGAF.pl`.

**Reference (do not modify):**
- `resources/AGI_LocusCode_UniProt_19.gene2acc` — already in place. 29924 lines, three TSV columns: source ID (`AGI_LocusCode:AT…` or `At…` lowercase), UniProt protein ID (may include isoform suffix `-N`), canonical AGI_LocusCode ID.
- `resources/TAIR10_TAIRlocusaccessionID_AGI_mapping.txt` and `resources/uniprot_to_araport_map_gaf.tsv` — kept on disk for archive / rollback, no longer referenced.

---

## Notes for the implementer

- The user's CLAUDE.md says **Claude must not run `git add` or `git commit`**. The `Commit` steps below are for the user to run manually (or for an executor that has explicit user permission). If you are executing this plan as Claude, run the `git status` / `git diff` checks and ask the user to commit.
- All commands assume the project root `/Users/ebertdu/panther/fullgo_paint_update`.
- There is no Perl test harness in the repo, and we are not adding one. Verification is a Perl one-liner spot check (Task 2) plus an end-to-end smoke run on a recent `BASE_PATH` (Task 6).
- Concrete reference example: `awk -F'\t' '$2=="P56537"' gene_association.paint_human.gaf` shows IBAs whose with/from columns currently contain `TAIR:locus:2078921|TAIR:locus:2063927`. After this fix these will read `AGI_LocusCode:AT…|AGI_LocusCode:AT…`.

---

### Task 1: Wire the AGI lookup into `scripts/createGAF.pl`

**Files:**
- Modify: `scripts/createGAF.pl`

This single task does five edits to one file. Follow the steps in order.

- [ ] **Step 1: Update the option-banner comment**

Find this banner near the top (around line 14):

```perl
##      -g go_aggregate (from database)
##      -t TAIR10_TAIRlocusaccessionID_AGI_mapping.txt
##      -c evidence (from database)
```

Change to:

```perl
##      -g go_aggregate (from database)
##      -t AGI_LocusCode_UniProt_<version>.gene2acc (TAIR/Araport -> AGI_LocusCode lookup)
##      -c evidence (from database)
```

- [ ] **Step 2: Drop `u:` from `getopts` and rewrite the option assignments**

Find the `getopts` line (around line 26):

```perl
getopts('o:i:a:q:g:P:n:N:G:b:C:r:t:u:p:c:T:e:w:R:s:UvVh') || &usage();
```

Change to (remove `u:`):

```perl
getopts('o:i:a:q:g:P:n:N:G:b:C:r:t:p:c:T:e:w:R:s:UvVh') || &usage();
```

Find the `$tair` / `$araport` option assignments (around lines 37–38):

```perl
$tair = $opt_t if ($opt_t);       # -t for the TAIR ID lookup file
$araport = $opt_u if ($opt_u);    # -u for the UniProt-to-Araport ID lookup file
```

Replace with:

```perl
$agi_lookup_file = $opt_t if ($opt_t);   # -t for the AGI_LocusCode lookup TSV
```

- [ ] **Step 3: Add the two helper subs near the top of the script**

Place them after the option-handling block and before the `Parse the profile file` section (around line 64, just before `my $go_version;`). Insert this code block:

```perl
###############################
# AGI_LocusCode lookup helpers
#
# parse_agi_lookup_file($path) reads a 3-column TSV (source_id,
# uniprot_id, canonical_agi_id) and returns two hashrefs:
#   $by_protein->{$uniprot_id}              = $canonical_agi
#   $by_geneid ->{ uc(prefix-stripped col1)} = $canonical_agi
#
# lookup_agi($geneId, $proteinId, $by_protein, $by_geneid) returns the
# canonical AGI_LocusCode:... string or undef. It strips a leading
# "<prefix>:" (e.g. "TAIR:", "Araport:", "UniProtKB:") from each input
# and prefers the UniProt match over the gene-id match.
###############################
sub parse_agi_lookup_file {
    my ($path) = @_;
    open my $fh, '<', $path or die "Could not open file $path: $!";
    my (%by_protein, %by_geneid);
    while (my $line = <$fh>) {
        chomp $line;
        next if $line eq '' || $line =~ /^#/;
        my ($source_id, $protein_id, $canonical_agi) = split(/\t/, $line);
        next unless defined $canonical_agi && $canonical_agi ne '';

        if (defined $protein_id && $protein_id ne '') {
            $by_protein{$protein_id} = $canonical_agi;
        }
        if (defined $source_id && $source_id ne '') {
            my $bare = $source_id;
            $bare =~ s/^\w+://;
            $by_geneid{uc($bare)} = $canonical_agi;
        }
    }
    close $fh;
    return (\%by_protein, \%by_geneid);
}

sub lookup_agi {
    my ($geneId, $proteinId, $by_protein, $by_geneid) = @_;

    my $bare_protein = defined $proteinId ? $proteinId : '';
    $bare_protein =~ s/^\w+://;
    my $bare_gene = defined $geneId ? $geneId : '';
    $bare_gene =~ s/^\w+://;

    if ($bare_protein ne '' && defined $by_protein->{$bare_protein}) {
        return $by_protein->{$bare_protein};
    }
    if ($bare_gene ne '' && defined $by_geneid->{uc($bare_gene)}) {
        return $by_geneid->{uc($bare_gene)};
    }
    return undef;
}
```

- [ ] **Step 4: Replace the TAIR + Araport hash-building blocks with one call**

Find this block (lines ~84–106):

```perl
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
```

Replace with:

```perl
######################################
# Parse AGI_LocusCode lookup TSV
# Provides ARATH UniProt-or-gene-id -> AGI_LocusCode:ATxGNNNNN
######################################
my ($agi_by_protein, $agi_by_geneid) = parse_agi_lookup_file($agi_lookup_file);
```

- [ ] **Step 5: Replace the two ARATH branches in leaf parsing with one `lookup_agi` call**

Find the two ARATH branches (lines ~249–272) inside the long `if/elsif` chain:

```perl
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
}
```

Replace with:

```perl
}elsif ($geneId=~/^TAIR/ || $geneId=~/^Araport/){
    my $agi = lookup_agi($geneId, $proteinId, $agi_by_protein, $agi_by_geneid);
    if (defined $agi) {
        $shortId = $agi;
    } else {
        print STDERR "ARATH leaf has no mapped AGI_LocusCode (longId=$longId).\n";
        next;
    }
}
```

- [ ] **Step 6: Compile-check**

Run: `perl -c scripts/createGAF.pl`

Expected: `scripts/createGAF.pl syntax OK`. Fix any new errors introduced by the edit before continuing.

---

### Task 2: Spot-check the helpers against the real lookup file

This is a non-destructive sanity check on the parser itself before touching the wrappers.

- [ ] **Step 1: Run the spot-check one-liner**

Run:
```bash
perl -e '
require "scripts/createGAF.pl";
' 2>&1 | head -5
```

Expected: this will likely error out because `createGAF.pl` is a script that runs at top level, not a `require`-able module. That is fine — we will not actually `require` it. Skip to Step 2.

- [ ] **Step 2: Inline the helpers into a quick Perl smoke test**

Run:
```bash
perl -e '
sub parse_agi_lookup_file {
    my ($path) = @_;
    open my $fh, "<", $path or die "Could not open file $path: $!";
    my (%by_protein, %by_geneid);
    while (my $line = <$fh>) {
        chomp $line;
        next if $line eq "" || $line =~ /^#/;
        my ($source_id, $protein_id, $canonical_agi) = split(/\t/, $line);
        next unless defined $canonical_agi && $canonical_agi ne "";
        $by_protein{$protein_id} = $canonical_agi if defined $protein_id && $protein_id ne "";
        if (defined $source_id && $source_id ne "") {
            my $bare = $source_id;
            $bare =~ s/^\w+://;
            $by_geneid{uc($bare)} = $canonical_agi;
        }
    }
    close $fh;
    return (\%by_protein, \%by_geneid);
}
sub lookup_agi {
    my ($geneId, $proteinId, $by_protein, $by_geneid) = @_;
    my $bp = defined $proteinId ? $proteinId : ""; $bp =~ s/^\w+://;
    my $bg = defined $geneId    ? $geneId    : ""; $bg =~ s/^\w+://;
    return $by_protein->{$bp} if $bp ne "" && defined $by_protein->{$bp};
    return $by_geneid->{uc($bg)} if $bg ne "" && defined $by_geneid->{uc($bg)};
    return undef;
}

my ($p, $g) = parse_agi_lookup_file("resources/AGI_LocusCode_UniProt_19.gene2acc");
print "by_protein size:  ", scalar(keys %$p), "\n";
print "by_geneid  size:  ", scalar(keys %$g), "\n";
print "Q0WV96  -> ",         lookup_agi("TAIR:locus",     "UniProtKB:Q0WV96",   $p, $g) // "UNDEF", "\n";
print "AT1G01070 (upper) -> ", lookup_agi("TAIR:AT1G01070", "UniProtKB:UNKNOWN", $p, $g) // "UNDEF", "\n";
print "At1g01070 (lower) -> ", lookup_agi("TAIR:At1g01070", "UniProtKB:UNKNOWN", $p, $g) // "UNDEF", "\n";
print "Q5XEZ0-2 (isoform) -> ", lookup_agi("TAIR:locus", "UniProtKB:Q5XEZ0-2", $p, $g) // "UNDEF", "\n";
print "unknown -> ",          lookup_agi("TAIR:UNKNOWN",   "UniProtKB:UNKNOWN",  $p, $g) // "UNDEF", "\n";
'
```

Expected output:
```
by_protein size:  29924
by_geneid  size:  <a number close to 29924, may be slightly less due to duplicate keys>
Q0WV96  -> AGI_LocusCode:AT1G01010
AT1G01070 (upper) -> AGI_LocusCode:AT1G01070
At1g01070 (lower) -> AGI_LocusCode:AT1G01070
Q5XEZ0-2 (isoform) -> AGI_LocusCode:AT1G01070
unknown -> UNDEF
```

If any line shows `UNDEF` where it should not, or the sizes look wildly off (e.g. 0), the inlined sub in `scripts/createGAF.pl` has a bug — fix and re-run.

- [ ] **Step 3: Stage and commit (user)**

Files in this commit:
- `scripts/createGAF.pl`

Suggested message:
```
Inline AGI_LocusCode lookup in createGAF.pl for #78
```

---

### Task 3: Update `Makefile`

**Files:**
- Modify: `Makefile` (lines 94–97)

- [ ] **Step 1: Replace the two old export blocks with one `AGI_MAP` export**

Find this block (lines 94–97):

```makefile
### -t TAIR10_TAIRlocusaccessionID_AGI_mapping.txt
export TAIR_MAP = resources/TAIR10_TAIRlocusaccessionID_AGI_mapping.txt
### -u Mapping to support "TAIR=locus" long IDs
export ARAPORT_MAP = resources/uniprot_to_araport_map_gaf.tsv
```

Replace with:

```makefile
### -t AGI_LocusCode lookup TSV used to render ARATH IDs as AGI_LocusCode:ATxGNNNNN
export AGI_MAP = resources/AGI_LocusCode_UniProt_19.gene2acc
```

- [ ] **Step 2: Verify nothing else references `TAIR_MAP` / `ARAPORT_MAP`**

Run:
```bash
grep -rnE "TAIR_MAP|ARAPORT_MAP" Makefile scripts/ 2>/dev/null
```
Expected: empty output. (After Task 4 also runs, this confirms zero references remain.)

---

### Task 4: Update `scripts/createGAF.sh` and `scripts/createGAF_uniprot.sh`

**Files:**
- Modify: `scripts/createGAF.sh`
- Modify: `scripts/createGAF_uniprot.sh`

- [ ] **Step 1: Update `scripts/createGAF.sh`**

Find this block:

```bash
-g $BASE_PATH/resources/$GO_AGG \
-t $TAIR_MAP \
-u $ARAPORT_MAP \
-c $BASE_PATH/resources/$EVIDENCE \
```

Replace with:

```bash
-g $BASE_PATH/resources/$GO_AGG \
-t $AGI_MAP \
-c $BASE_PATH/resources/$EVIDENCE \
```

- [ ] **Step 2: Update `scripts/createGAF_uniprot.sh`**

Make the identical change in `scripts/createGAF_uniprot.sh` (`-t $TAIR_MAP -u $ARAPORT_MAP` → `-t $AGI_MAP`).

- [ ] **Step 3: Confirm no other shell/slurm script references the old vars**

Run:
```bash
grep -rnE "TAIR_MAP|ARAPORT_MAP" Makefile scripts/ 2>/dev/null
```
Expected: empty output.

- [ ] **Step 4: Verify the `create_gafs` recipe still parses**

Run: `make -n create_gafs 2>&1 | head -30`

Expected: the dry-run prints commands without "TAIR_MAP undefined" or similar errors. The output should include `-t resources/AGI_LocusCode_UniProt_19.gene2acc` and **no** `-u` flag. Pipeline-time warnings about missing `BASE_PATH` files are fine — those exist only at run time.

- [ ] **Step 5: Stage and commit (user)**

Files in this commit:
- `Makefile`
- `scripts/createGAF.sh`
- `scripts/createGAF_uniprot.sh`

Suggested message:
```
Switch createGAF wrappers to AGI_MAP (#78)
```

---

### Task 5: Delete the orphaned `scripts/createGAF_human_exp_references.pl`

**Files:**
- Delete: `scripts/createGAF_human_exp_references.pl`

- [ ] **Step 1: Verify no caller references it**

Run:
```bash
grep -rn "createGAF_human_exp_references" Makefile scripts/ docs/ tests/ 2>/dev/null
```
Expected: empty output. The script is not invoked from any Makefile recipe, shell wrapper, slurm script, doc, or test. (If anything matches, stop and reassess with the user — the script may still be in use.)

- [ ] **Step 2: Delete the file**

Run:
```bash
rm scripts/createGAF_human_exp_references.pl
```

- [ ] **Step 3: Re-confirm nothing references the now-removed file**

Run:
```bash
grep -rn "createGAF_human_exp_references" . 2>/dev/null
```
Expected: empty output (now also empty in `.git/`-excluded text files in the working tree).

- [ ] **Step 4: Stage and commit (user)**

Suggested message:
```
Delete orphaned createGAF_human_exp_references.pl
```

---

### Task 6: End-to-end smoke verification

The full PAINT pipeline can only run on the HPC machine with database access, so this task verifies the change against the most recent local `BASE_PATH` directory (or any directory containing the inputs needed by `createGAF.sh`).

- [ ] **Step 1: Pick a recent BASE_PATH that has the createGAF inputs**

Run:
```bash
ls -d 20*-*-*_fullgo* 2>/dev/null | tail -5
```

Pick the most recent directory (e.g. `2025-12-15_fullgo`) that contains both `resources/paint_annotation` and `resources/organism_taxon`. Call this `$SMOKE_BASE` for the rest of the task.

- [ ] **Step 2: Capture a "before" sample of ARATH IDs from the previous output (if available)**

If the chosen `$SMOKE_BASE` already has an `IBA_GAFs/` directory from a prior run:
```bash
grep -c "TAIR:locus:"  $SMOKE_BASE/IBA_GAFs/gene_association.paint_human.gaf
grep -c "AGI_LocusCode:" $SMOKE_BASE/IBA_GAFs/gene_association.paint_human.gaf
```

Record the two counts. Pre-fix expectation: many `TAIR:locus:` matches, zero `AGI_LocusCode:`.

- [ ] **Step 3: Re-run `createGAF.sh` against the same BASE_PATH**

Activate the same Make context the pipeline uses:
```bash
BASE_PATH=$SMOKE_BASE PANTHER_VERSION=19.0 make -n create_gafs | head -20
```
Confirm the printed command line includes `-t resources/AGI_LocusCode_UniProt_19.gene2acc` and **no** `-u` flag. If it does, run for real:
```bash
BASE_PATH=$SMOKE_BASE PANTHER_VERSION=19.0 make create_gafs
```

(If `make create_gafs` requires SLURM and is unsafe to run locally, run `scripts/createGAF.sh` directly with the same exported variables instead.)

- [ ] **Step 4: Spot-check the regenerated GAFs**

Run:
```bash
grep -c "TAIR:locus:"   $SMOKE_BASE/IBA_GAFs/gene_association.paint_human.gaf
grep -c "AGI_LocusCode:" $SMOKE_BASE/IBA_GAFs/gene_association.paint_human.gaf
grep -c "TAIR:locus:"   $SMOKE_BASE/IBA_GAFs/gene_association.paint_tair.gaf
grep -c "AGI_LocusCode:" $SMOKE_BASE/IBA_GAFs/gene_association.paint_tair.gaf
```

Expected:
- `TAIR:locus:` count is **0** in both files.
- `AGI_LocusCode:` count is non-zero, comparable to the previous `TAIR:locus:` count.

- [ ] **Step 5: Spot-check the user's reference example**

Run:
```bash
awk -F'\t' '$2=="P56537"' $SMOKE_BASE/IBA_GAFs/gene_association.paint_human.gaf \
  | grep -oE "(TAIR:locus:[0-9]+|AGI_LocusCode:AT[0-9]+G[0-9]+)" \
  | sort -u
```

Expected: only `AGI_LocusCode:AT…` matches; no `TAIR:locus:…`.

- [ ] **Step 6: Spot-check the tair output filename and primary column**

Run:
```bash
head -3 $SMOKE_BASE/IBA_GAFs/gene_association.paint_tair.gaf
awk -F'\t' '{print $1}' $SMOKE_BASE/IBA_GAFs/gene_association.paint_tair.gaf | sort -u | head
```

Expected:
- File path is still `gene_association.paint_tair.gaf` (we did not rename the file).
- Column 1 in the tair gaf shows `AGI_LocusCode` (not `TAIR`).

- [ ] **Step 7: Skim the stderr log for unmapped ARATH leaves**

Run:
```bash
grep "ARATH leaf has no mapped AGI_LocusCode" $SMOKE_BASE/err | wc -l
grep "ARATH leaf has no mapped AGI_LocusCode" $SMOKE_BASE/err | head
```

Expected: small or zero count. If non-trivial, capture the offending leaves and decide with the user whether they need adding to the lookup file. Do not silently widen the lookup logic.

- [ ] **Step 8: Report results to the user**

Hand the user a short summary:
- Old `TAIR:locus:` count vs new (should drop to 0).
- New `AGI_LocusCode:` count.
- Any unmapped-ARATH-leaf warnings.

---

## Self-Review Checklist (already run by author of this plan)

- **Spec coverage:** Every requirement from issue #78 is covered. The issue asks for `AGI_LocusCode:` output in IBA GAFs — Task 1 changes the IDs; Task 6 verifies the output. The user's pre-built lookup file is consumed by Tasks 3 and 4. The issue's note that the existing TAIR/Araport handling can be replaced wholesale is addressed by Task 1 Steps 4 and 5. Task 5 deletes the orphaned reference script per the user's direction. ✓
- **Placeholder scan:** No "TBD", "TODO", or "fill in details" remain. All Perl, Bash, and Make snippets are complete. ✓
- **Type / name consistency:** `parse_agi_lookup_file` and `lookup_agi` are referenced consistently across Tasks 1 and 2. The hashref names `$agi_by_protein` / `$agi_by_geneid` are consistent. The Make variable name `AGI_MAP` is consistent across the Makefile and both shell wrappers. ✓
