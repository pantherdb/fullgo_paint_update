import importlib.util
import os

import pytest
import requests

SCRIPTS_DIR = os.path.join(os.path.dirname(__file__), "..", "scripts")


def load_downloader(module_name):
    spec = importlib.util.spec_from_file_location(
        module_name, os.path.join(SCRIPTS_DIR, f"{module_name}.py")
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class FakeResponse:
    """Minimal stand-in for a streamed requests.Response."""

    def __init__(self, chunks, headers):
        self.chunks = chunks
        self.headers = headers

    def __enter__(self):
        return self

    def __exit__(self, *exc_info):
        return False

    def iter_content(self, chunk_size=None):
        return iter(self.chunks)


class FakeListingResponse:
    """Minimal stand-in for a directory-listing requests.Response."""

    def __init__(self, status_code, text):
        self.status_code = status_code
        self.text = text

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError(f"{self.status_code} Client Error")


@pytest.fixture(params=["download_fullgo", "download_goex"])
def downloader(request, monkeypatch):
    """Both downloaders carry the same download_files() implementation."""
    module = load_downloader(request.param)

    def _install(chunks, headers):
        monkeypatch.setattr(
            module.requests, "get", lambda url, stream=False: FakeResponse(chunks, headers)
        )
        return module

    return _install


def test_download_files_with_content_length(downloader, tmp_path):
    module = downloader([b"abc", b"de"], {"Content-Length": "5"})
    module.download_files("https://example.org/", ["ontology/go.obo"], str(tmp_path))
    assert (tmp_path / "go.obo").read_bytes() == b"abcde"


def test_download_files_without_content_length(downloader, tmp_path):
    """CloudFront gzips go.json on the fly, so no Content-Length is sent."""
    module = downloader([b"{}"], {"Content-Encoding": "gzip", "Transfer-Encoding": "chunked"})
    module.download_files("https://example.org/", ["ontology/go.json"], str(tmp_path))
    assert (tmp_path / "go.json").read_bytes() == b"{}"


@pytest.mark.parametrize("module_name", ["download_fullgo", "download_goex"])
def test_get_directory_listing_raises_on_error_status(module_name, monkeypatch):
    """A listing URL missing its trailing slash 403s; that must not read as 'no files'."""
    module = load_downloader(module_name)
    monkeypatch.setattr(
        module.requests, "get", lambda url: FakeListingResponse(403, "<Error><Code>AccessDenied</Code></Error>")
    )
    with pytest.raises(requests.HTTPError):
        module.get_directory_listing("https://example.org/annotations/gaf")


@pytest.mark.parametrize("module_name", ["download_fullgo", "download_goex"])
def test_get_directory_listing_parses_hrefs(module_name, monkeypatch):
    module = load_downloader(module_name)
    html = '<a href="ACIB2-uniprot.gaf.gz">a</a><a href="ANOCA-uniprot.gaf.gz">b</a>'
    monkeypatch.setattr(module.requests, "get", lambda url: FakeListingResponse(200, html))
    assert module.get_directory_listing("https://example.org/annotations/gaf/") == [
        "ACIB2-uniprot.gaf.gz", "ANOCA-uniprot.gaf.gz"
    ]


ANNOTATION_LISTING = [
    "index.html",
    "ACIB2-uniprot.gaf.gz",
    "ARATH-mod.gaf.gz",
    "ARATH-uniprot.gaf.gz",
    "DANRE-mod.gaf.gz",
    "DANRE-uniprot.gaf.gz",
    "goa_uniprot_all_noiea.gaf.gz",
]


def test_select_gaf_files_defaults_to_uniprot():
    """Long-term pipeline goal is UniProt-only, so no flag means no -mod files."""
    module = load_downloader("download_fullgo")
    assert module.select_gaf_files(ANNOTATION_LISTING) == [
        "ACIB2-uniprot.gaf.gz", "ARATH-uniprot.gaf.gz", "DANRE-uniprot.gaf.gz"
    ]


def test_select_gaf_files_prefers_mod_when_available():
    """-uniprot can drop annotations vs -mod (e.g. DANRE), hence the opt-in flag."""
    module = load_downloader("download_fullgo")
    assert module.select_gaf_files(ANNOTATION_LISTING, prefer_mod=True) == [
        "ACIB2-uniprot.gaf.gz", "ARATH-mod.gaf.gz", "DANRE-mod.gaf.gz"
    ]


def test_select_gaf_files_prefers_mod_for_species_without_uniprot():
    module = load_downloader("download_fullgo")
    assert module.select_gaf_files(["FOO-mod.gaf.gz"], prefer_mod=True) == ["FOO-mod.gaf.gz"]


def test_select_gaf_files_skips_mod_only_species_by_default():
    module = load_downloader("download_fullgo")
    assert module.select_gaf_files(["FOO-mod.gaf.gz"]) == []


def test_select_gaf_files_handles_listing_paths():
    """Some listings hand back paths rather than bare filenames."""
    module = load_downloader("download_fullgo")
    listing = ["/annotations/gaf/DANRE-mod.gaf.gz", "/annotations/gaf/DANRE-uniprot.gaf.gz"]
    assert module.select_gaf_files(listing, prefer_mod=True) == ["/annotations/gaf/DANRE-mod.gaf.gz"]
