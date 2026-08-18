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


### Per-proteome source overrides
#
# PANTHER cannot map every MOD ID namespace. Switching ECOLI (EcoCyc), XENLA (Xenbase) and
# SCHJY (JaponicusDB) to -mod dropped their Pthr_GO annotations by 98.8%, 40.7% and 100%,
# while DANRE (ZFIN) gained 44.7%. The breakage is per-proteome, not per-namespace: XENTR is
# also Xenbase and survived. So each proteome's source is overridable either way.

BOTH_SOURCES_LISTING = [
    "ACIB2-uniprot.gaf.gz",
    "DANRE-mod.gaf.gz", "DANRE-uniprot.gaf.gz",
    "ECOLI-mod.gaf.gz", "ECOLI-uniprot.gaf.gz",
    "SCHJY-mod.gaf.gz", "SCHJY-uniprot.gaf.gz",
]


def write_source_file(tmp_path, text):
    path = tmp_path / "gaf_source_by_proteome.tsv"
    path.write_text(text)
    return str(path)


def test_source_override_takes_mod_when_the_default_is_uniprot():
    """An 'always-mod' entry: DANRE gets -mod with no --prefer_mod flag at all."""
    module = load_downloader("download_fullgo")
    selected = module.select_gaf_files(BOTH_SOURCES_LISTING, source_by_proteome={"DANRE": "mod"})
    assert selected == [
        "ACIB2-uniprot.gaf.gz", "DANRE-mod.gaf.gz", "ECOLI-uniprot.gaf.gz", "SCHJY-uniprot.gaf.gz"
    ]


def test_source_override_takes_uniprot_when_the_default_is_mod():
    """The never-mod case this whole file exists for."""
    module = load_downloader("download_fullgo")
    never_mod = {"ECOLI": "uniprot", "SCHJY": "uniprot"}
    selected = module.select_gaf_files(
        BOTH_SOURCES_LISTING, prefer_mod=True, source_by_proteome=never_mod)
    assert selected == [
        "ACIB2-uniprot.gaf.gz", "DANRE-mod.gaf.gz", "ECOLI-uniprot.gaf.gz", "SCHJY-uniprot.gaf.gz"
    ]


def test_unlisted_proteomes_follow_the_uniprot_default():
    module = load_downloader("download_fullgo")
    selected = module.select_gaf_files(BOTH_SOURCES_LISTING, source_by_proteome={"DANRE": "mod"})
    assert "ECOLI-uniprot.gaf.gz" in selected and "ECOLI-mod.gaf.gz" not in selected


def test_unlisted_proteomes_follow_the_mod_default():
    module = load_downloader("download_fullgo")
    selected = module.select_gaf_files(
        BOTH_SOURCES_LISTING, prefer_mod=True, source_by_proteome={"ECOLI": "uniprot"})
    assert "SCHJY-mod.gaf.gz" in selected and "SCHJY-uniprot.gaf.gz" not in selected


def test_mod_override_falls_back_to_uniprot_when_no_mod_file_is_listed(capsys):
    module = load_downloader("download_fullgo")
    selected = module.select_gaf_files(
        ["ACIB2-uniprot.gaf.gz"], source_by_proteome={"ACIB2": "mod"})
    assert selected == ["ACIB2-uniprot.gaf.gz"]
    assert "ACIB2" in capsys.readouterr().out


def test_mod_default_falls_back_quietly(capsys):
    """Most species publish no -mod file, so --prefer_mod must not warn 150 times."""
    module = load_downloader("download_fullgo")
    module.select_gaf_files(["ACIB2-uniprot.gaf.gz"], prefer_mod=True)
    assert "ACIB2" not in capsys.readouterr().out


def test_uniprot_override_skips_a_proteome_that_only_publishes_mod(capsys):
    """An explicit uniprot must never silently fall back to the source it banned."""
    module = load_downloader("download_fullgo")
    selected = module.select_gaf_files(
        ["SCHJY-mod.gaf.gz"], prefer_mod=True, source_by_proteome={"SCHJY": "uniprot"})
    assert selected == []
    assert "SCHJY" in capsys.readouterr().out


def test_select_gaf_files_warns_on_an_override_for_an_absent_proteome(capsys):
    """A stale entry silently doing nothing is how this bites us again."""
    module = load_downloader("download_fullgo")
    module.select_gaf_files(BOTH_SOURCES_LISTING, source_by_proteome={"NOSUCH": "uniprot"})
    assert "NOSUCH" in capsys.readouterr().out


### read_source_by_proteome

def test_read_source_by_proteome_parses_entries(tmp_path):
    module = load_downloader("download_fullgo")
    path = write_source_file(tmp_path, "ECOLI\tuniprot\nDANRE\tmod\n")
    assert module.read_source_by_proteome(path) == {"ECOLI": "uniprot", "DANRE": "mod"}


def test_read_source_by_proteome_ignores_comments_and_blank_lines(tmp_path):
    module = load_downloader("download_fullgo")
    path = write_source_file(tmp_path, "# a header\n\nECOLI\tuniprot\n\n#DANRE\tmod\n")
    assert module.read_source_by_proteome(path) == {"ECOLI": "uniprot"}


def test_read_source_by_proteome_strips_trailing_comments(tmp_path):
    """Each entry carries its rationale inline; that is the point of the file."""
    module = load_downloader("download_fullgo")
    path = write_source_file(tmp_path, "ECOLI\tuniprot\t# EcoCyc IDs; 54,316 -> 677 (-98.8%)\n")
    assert module.read_source_by_proteome(path) == {"ECOLI": "uniprot"}


def test_read_source_by_proteome_accepts_whitespace_separation(tmp_path):
    module = load_downloader("download_fullgo")
    path = write_source_file(tmp_path, "  ECOLI   uniprot  \n")
    assert module.read_source_by_proteome(path) == {"ECOLI": "uniprot"}


def test_read_source_by_proteome_upcases_proteome_codes(tmp_path):
    """A lowercase typo must not silently leave a banned proteome on -mod."""
    module = load_downloader("download_fullgo")
    path = write_source_file(tmp_path, "ecoli\tUniProt\n")
    assert module.read_source_by_proteome(path) == {"ECOLI": "uniprot"}


def test_read_source_by_proteome_rejects_an_unknown_source(tmp_path):
    module = load_downloader("download_fullgo")
    path = write_source_file(tmp_path, "ECOLI\tecocyc\n")
    with pytest.raises(ValueError, match="ecocyc"):
        module.read_source_by_proteome(path)


def test_read_source_by_proteome_rejects_a_malformed_line(tmp_path):
    module = load_downloader("download_fullgo")
    path = write_source_file(tmp_path, "ECOLI\n")
    with pytest.raises(ValueError, match="ECOLI"):
        module.read_source_by_proteome(path)


def test_load_source_by_proteome_raises_for_a_missing_explicit_path(tmp_path):
    module = load_downloader("download_fullgo")
    with pytest.raises(FileNotFoundError):
        module.load_source_by_proteome(str(tmp_path / "nope.tsv"))


def test_load_source_by_proteome_tolerates_the_default_file_being_absent(monkeypatch, tmp_path):
    module = load_downloader("download_fullgo")
    missing = str(tmp_path / "gone.tsv")
    monkeypatch.setattr(module, "DEFAULT_SOURCE_BY_PROTEOME", missing)
    assert module.load_source_by_proteome(missing) == {}


### The committed override file

def test_repo_source_file_bans_mod_for_the_proteomes_it_broke():
    module = load_downloader("download_fullgo")
    sources = module.read_source_by_proteome(module.DEFAULT_SOURCE_BY_PROTEOME)
    assert sources["ECOLI"] == "uniprot"
    assert sources["XENLA"] == "uniprot"
    assert sources["SCHJY"] == "uniprot"


def test_repo_source_file_keeps_danre_on_mod():
    module = load_downloader("download_fullgo")
    assert module.read_source_by_proteome(module.DEFAULT_SOURCE_BY_PROTEOME)["DANRE"] == "mod"
