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
                pbar = tqdm(total=int(r.headers['Content-Length']))
                for chunk in r.iter_content(chunk_size=8192): 
                    f.write(chunk)
                    pbar.update(len(chunk))


def get_directory_listing(full_dir_url):
    r = requests.get(full_dir_url)
    data = bs4.BeautifulSoup(r.text, "html.parser")
    file_list = [l["href"] for l in data.find_all("a")]
    return file_list


if __name__ == "__main__":
    args = parser.parse_args()

    # Append downloaded file URLs for later reporting (e.g. in README)
    download_logfile = open(f"{args.fullgo_working_dir}/downloaded_files.txt", "a")

    # Download release GAFs - all GAFs in URL directory
    # annotations_dir_url = f"{args.go_download_base_url}/annotations/"
    annotations_dir_url = urllib.parse.urljoin(args.go_download_base_url, "annotations/")
    annotation_files = get_directory_listing(annotations_dir_url)
    gaf_files = [af for af in annotation_files if af.endswith(".gaf.gz")]

    gaf_files.append("products/annotations/paint_other.gaf.gz")  # Don't forget our paint_other
    
    download_files(args.go_download_base_url, gaf_files, args.gaf_files_dir, download_logfile)

    # Download metadata/release-date.json and metadata/release-archive-doi.json
    metadata_files = ["metadata/release-date.json", "metadata/release-archive-doi.json"]
    download_files(args.go_download_base_url, metadata_files, args.fullgo_working_dir, download_logfile)

    # Download ontology files ontology/go.obo and ontology/extensions/go-gaf.owl
    ontology_files = ["ontology/go.obo", "ontology/extensions/go-gaf.owl"]
    download_files(args.go_download_base_url, ontology_files, args.fullgo_working_dir, download_logfile)

    download_logfile.close()