import argparse
import requests
import bs4
import urllib
import os
from tqdm import *


parser = argparse.ArgumentParser()
parser.add_argument('-d', '--fullgo_working_dir', help="BASE_PATH containing fullgo_paint_update files for current release")
parser.add_argument('-g', '--gaf_files_dir', help="Path to directory where downloaded .gaf files will be saved")
parser.add_argument('-u', '--go_download_base_url', help="Usually http://current.geneontology.org/")
parser.add_argument('-m', '--prefer_mod', action='store_true',
                    help="Download a species' -mod.gaf.gz instead of its -uniprot.gaf.gz whenever "
                         "the -mod file exists. Default (no flag) is -uniprot only, the long-term "
                         "pipeline goal; use this while a -uniprot file is dropping annotations.")

UNIPROT_SUFFIX = "-uniprot.gaf.gz"
MOD_SUFFIX = "-mod.gaf.gz"
UNIPROT_SOURCE = "uniprot"
MOD_SOURCE = "mod"
GAF_SOURCES = (UNIPROT_SOURCE, MOD_SOURCE)

DEFAULT_SOURCE_BY_PROTEOME = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "resources", "gaf_source_by_proteome.tsv")

parser.add_argument('-s', '--gaf_source_by_proteome', default=DEFAULT_SOURCE_BY_PROTEOME,
                    help="Per-proteome override of the -uniprot/-mod choice, overriding whatever "
                         "--prefer_mod would pick. PANTHER cannot map every MOD ID namespace "
                         f"(see {os.path.basename(DEFAULT_SOURCE_BY_PROTEOME)}, the default)")


def read_source_by_proteome(path):
    """Parse the per-proteome source overrides into {PROTEOME: "uniprot"|"mod"}.

    Two whitespace-separated columns, # comments anywhere. Proteome codes are upcased so a
    lowercase typo cannot silently leave a banned proteome on its -mod GAF.
    """
    source_by_proteome = {}
    with open(path) as f:
        for line_number, line in enumerate(f, start=1):
            fields = line.split("#", 1)[0].split()
            if not fields:
                continue
            if len(fields) != 2:
                raise ValueError(
                    f"{path} line {line_number}: expected 'PROTEOME source', got {line.strip()!r}")
            proteome, source = fields[0].upper(), fields[1].lower()
            if source not in GAF_SOURCES:
                raise ValueError(
                    f"{path} line {line_number}: source must be one of {GAF_SOURCES}, got {source!r}")
            source_by_proteome[proteome] = source
    return source_by_proteome


def load_source_by_proteome(path):
    """Read the overrides, tolerating only the default file being absent."""
    if os.path.isfile(path):
        return read_source_by_proteome(path)
    if os.path.abspath(path) != os.path.abspath(DEFAULT_SOURCE_BY_PROTEOME):
        raise FileNotFoundError(f"No GAF source override file at {path}")
    print(f"No {path}; every proteome follows the global default")
    return {}


def select_gaf_files(annotation_files, prefer_mod=False, source_by_proteome=None):
    """Pick one release GAF per species code out of a directory listing.

    The global default is every -uniprot.gaf.gz, or -mod-where-available under prefer_mod.
    source_by_proteome overrides that per proteome in either direction: an explicit "mod"
    takes the -mod file with no flag, an explicit "uniprot" refuses -mod even under the flag.
    """
    source_by_proteome = source_by_proteome or {}
    default_source = MOD_SOURCE if prefer_mod else UNIPROT_SOURCE

    uniprot_files = {}
    mod_files = {}
    for af in annotation_files:
        basename = os.path.basename(af)
        if basename.endswith(UNIPROT_SUFFIX):
            uniprot_files[basename[:-len(UNIPROT_SUFFIX)]] = af
        elif basename.endswith(MOD_SUFFIX):
            mod_files[basename[:-len(MOD_SUFFIX)]] = af

    species_codes = list(uniprot_files)
    species_codes.extend(sc for sc in mod_files if sc not in uniprot_files)

    # A stale override doing nothing silently is how a proteome gets gutted again.
    for proteome in source_by_proteome:
        if proteome not in uniprot_files and proteome not in mod_files:
            print(f"WARNING: GAF source override for {proteome} matches no species in the listing")

    selected = []
    for species_code in species_codes:
        override = source_by_proteome.get(species_code)
        source = override or default_source
        if source == MOD_SOURCE:
            if species_code in mod_files:
                selected.append(mod_files[species_code])
            else:
                # Only an explicit override is worth warning about; most species publish no
                # -mod file at all, so prefer_mod falling back is the normal case.
                if override:
                    print(f"WARNING: {species_code} is set to mod but no {species_code}"
                          f"{MOD_SUFFIX} is listed; falling back to -uniprot")
                selected.append(uniprot_files[species_code])
        elif species_code in uniprot_files:
            selected.append(uniprot_files[species_code])
        elif override:
            # Never fall back to the source an override banned outright.
            print(f"WARNING: {species_code} is set to uniprot but no {species_code}"
                  f"{UNIPROT_SUFFIX} is listed; skipping this proteome")
    return selected


def download_files(base_url, file_relative_paths, dest_dir, download_logfile=None):
    for fp in file_relative_paths:
        full_url = fp
        if not full_url.startswith(base_url):
            full_url = urllib.parse.urljoin(base_url, fp)
        print(full_url)  # Also print size, download time?
        if download_logfile:
            download_logfile.write(f"{full_url}\n")
        # Save to dest_dir
        basename = os.path.basename(full_url)
        # print(basename)
        dest_fullpath = os.path.join(dest_dir, basename)
        with requests.get(full_url, stream=True) as r:
            with open(dest_fullpath, 'wb') as f:
                # No Content-Length when the server compresses on the fly (e.g. go.json
                # via CloudFront); tqdm handles total=None as an unbounded progress bar.
                content_length = r.headers.get('Content-Length')
                pbar = tqdm(total=int(content_length) if content_length else None)
                for chunk in r.iter_content(chunk_size=8192): 
                    f.write(chunk)
                    pbar.update(len(chunk))


def get_directory_listing(full_dir_url):
    r = requests.get(full_dir_url)
    # A listing URL missing its trailing slash 403s, which used to yield an empty
    # file list and silently download nothing.
    r.raise_for_status()
    data = bs4.BeautifulSoup(r.text, "html.parser")
    file_list = [l["href"] for l in data.find_all("a")]
    return file_list


if __name__ == "__main__":
    args = parser.parse_args()

    # Append downloaded file URLs for later reporting (e.g. in README)
    download_logfile = open(f"{args.fullgo_working_dir}/downloaded_files.txt", "a")

    # Download release GAFs - all GAFs in URL directory
    # annotations_dir_url = f"{args.go_download_base_url}/annotations/"
    annotations_dir_url = urllib.parse.urljoin(args.go_download_base_url, "annotations/gaf/")
    annotation_files = get_directory_listing(annotations_dir_url)
    source_by_proteome = load_source_by_proteome(args.gaf_source_by_proteome)
    gaf_files = select_gaf_files(annotation_files, prefer_mod=args.prefer_mod,
                                 source_by_proteome=source_by_proteome)
    if not gaf_files:
        raise RuntimeError(f"No species GAF files listed at {annotations_dir_url}")
    mod_count = sum(1 for gf in gaf_files if gf.endswith(MOD_SUFFIX))
    default_source = "mod-where-available" if args.prefer_mod else "uniprot"
    print(f"GAF sources: {mod_count} -mod of {len(gaf_files)} species "
          f"(default {default_source}, {len(source_by_proteome)} per-proteome overrides)")

    download_files(args.go_download_base_url, gaf_files, args.gaf_files_dir, download_logfile)

    # Download metadata/release-date.json and metadata/release-archive-doi.json
    metadata_files = ["metadata/release-date.json", "metadata/release-archive-doi.json"]
    download_files(args.go_download_base_url, metadata_files, args.fullgo_working_dir, download_logfile)

    # Download ontology files ontology/go.obo and ontology/extensions/go-gaf.owl
    ontology_files = ["ontology/go.obo", "ontology/extensions/go-gaf.owl", "ontology/go.json"]
    download_files(args.go_download_base_url, ontology_files, args.fullgo_working_dir, download_logfile)

    # Download subset files
    subset_files = ["ontology/subsets/gocheck_do_not_annotate.owl"]
    download_files(args.go_download_base_url, subset_files, args.fullgo_working_dir, download_logfile)

    download_logfile.close()