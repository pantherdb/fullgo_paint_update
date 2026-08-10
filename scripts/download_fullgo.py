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


def select_gaf_files(annotation_files, prefer_mod=False):
    """Pick one release GAF per species code out of a directory listing.

    Default is every -uniprot.gaf.gz. With prefer_mod, a species' -mod.gaf.gz wins
    whenever it is listed, so species with only a -mod file are picked up too.
    """
    uniprot_files = {}
    mod_files = {}
    for af in annotation_files:
        basename = os.path.basename(af)
        if basename.endswith(UNIPROT_SUFFIX):
            uniprot_files[basename[:-len(UNIPROT_SUFFIX)]] = af
        elif basename.endswith(MOD_SUFFIX):
            mod_files[basename[:-len(MOD_SUFFIX)]] = af
    if not prefer_mod:
        return list(uniprot_files.values())
    species_codes = list(uniprot_files)
    species_codes.extend(sc for sc in mod_files if sc not in uniprot_files)
    return [mod_files[sc] if sc in mod_files else uniprot_files[sc] for sc in species_codes]


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
    gaf_files = select_gaf_files(annotation_files, prefer_mod=args.prefer_mod)
    if not gaf_files:
        raise RuntimeError(f"No species GAF files listed at {annotations_dir_url}")
    if args.prefer_mod:
        mod_count = sum(1 for gf in gaf_files if gf.endswith(MOD_SUFFIX))
        print(f"Preferring -mod GAFs: {mod_count} of {len(gaf_files)} species")

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