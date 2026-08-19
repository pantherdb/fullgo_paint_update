"""Tests for scripts/transfer_release_files.py.

The three hops the pipeline needs, none of which the Makefile used to automate:
cluster -> local (fetch), local -> DB server load_dir (push_db), local -> file server
and HPC archive (push_gafs). A firewall blocks HPC from reaching the DB server, so the
local workstation is the relay.
"""

import os
import sys

import pytest

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(REPO_ROOT, "scripts"))

import transfer_release_files as trf  # noqa: E402


class FakeRunner:
    """Records argv instead of running it; hands back canned stdout for captures."""

    def __init__(self, stdout=""):
        self.commands = []
        self.stdout = stdout
        self.returncode = 0

    def __call__(self, cmd, capture=False):
        self.commands.append(cmd)
        return trf.CommandResult(self.returncode, self.stdout if capture else "")

    def joined(self):
        return [" ".join(c) for c in self.commands]

    def rsyncs(self):
        return [c for c in self.commands if c[0] == "rsync"]

    def sshes(self):
        return [c for c in self.commands if c[0] == "ssh"]


### Manifest

def test_manifest_templates_the_panther_version():
    paths = [f.path for f in trf.release_files("20.0")]
    assert "Pthr_GO_20.0.tsv" in paths
    assert "Pthr_GO_20.0_filtered.tsv" in paths
    assert not any("{panther_version}" in p for p in paths)


def test_db_load_subset_is_exactly_the_four_copy_files():
    """These four are the only paths any {load_dir} COPY statement names."""
    assert [f.path for f in trf.db_load_files("19.0")] == [
        "Pthr_GO_19.0.tsv",
        "Pthr_GO_19.0_filtered.tsv",
        "inputforGOClassification.tsv",
        "goparentchild.tsv",
    ]


def test_every_manifest_entry_records_who_needs_it():
    assert all(f.needed_by for f in trf.release_files("19.0"))


### fetch

def remote_listing(remote_base, names):
    return "".join(f"{remote_base}/{n}\n" for n in names)


def test_fetch_probes_for_both_plain_and_gz_variants():
    runner = FakeRunner(stdout="")
    trf.main(["fetch", "-H", "hpc", "-r", "/hpc/base", "-l", "/tmp/x"], runner=runner)
    probe = runner.sshes()[0]
    assert probe[:2] == ["ssh", "hpc"]
    assert "/hpc/base/go.json" in probe[2]
    assert "/hpc/base/go.json.gz" in probe[2]


def test_fetch_prefers_the_gz_variant_when_both_exist(tmp_path):
    runner = FakeRunner(stdout=remote_listing("/hpc/base", ["profile.txt", "profile.txt.gz"]))
    trf.main(["fetch", "-H", "hpc", "-r", "/hpc/base", "-l", str(tmp_path), "--no_fail"],
             runner=runner)
    sources = [c[-2] for c in runner.rsyncs()]
    assert "hpc:/hpc/base/profile.txt.gz" in sources
    assert "hpc:/hpc/base/profile.txt" not in sources


def test_fetch_uses_the_plain_variant_when_no_gz_exists(tmp_path):
    runner = FakeRunner(stdout=remote_listing("/hpc/base", ["profile.txt"]))
    trf.main(["fetch", "-H", "hpc", "-r", "/hpc/base", "-l", str(tmp_path), "--no_fail"],
             runner=runner)
    assert "hpc:/hpc/base/profile.txt" in [c[-2] for c in runner.rsyncs()]


def test_fetch_skips_wire_compression_for_already_gzipped_files(tmp_path):
    runner = FakeRunner(stdout=remote_listing("/hpc/base", ["profile.txt.gz"]))
    trf.main(["fetch", "-H", "hpc", "-r", "/hpc/base", "-l", str(tmp_path), "--no_fail"],
             runner=runner)
    gz_rsync = next(c for c in runner.rsyncs() if c[-2].endswith(".gz"))
    assert "-z" not in gz_rsync


def test_fetch_compresses_the_wire_for_plain_files(tmp_path):
    runner = FakeRunner(stdout=remote_listing("/hpc/base", ["profile.txt"]))
    trf.main(["fetch", "-H", "hpc", "-r", "/hpc/base", "-l", str(tmp_path), "--no_fail"],
             runner=runner)
    assert "-z" in next(c for c in runner.rsyncs() if c[-2].endswith("profile.txt"))


def test_fetch_exits_nonzero_when_a_required_file_is_missing_on_the_cluster(tmp_path, capsys):
    runner = FakeRunner(stdout=remote_listing("/hpc/base", ["profile.txt"]))
    exit_code = trf.main(["fetch", "-H", "hpc", "-r", "/hpc/base", "-l", str(tmp_path)],
                         runner=runner)
    assert exit_code != 0
    assert "goparentchild.tsv" in capsys.readouterr().out


def test_fetch_creates_the_local_resources_subdirectory(tmp_path):
    runner = FakeRunner(
        stdout=remote_listing("/hpc/base", ["resources/complex_terms.tsv"]))
    trf.main(["fetch", "-H", "hpc", "-r", "/hpc/base", "-l", str(tmp_path), "--no_fail"],
             runner=runner)
    assert (tmp_path / "resources").is_dir()


def test_fetch_dry_run_transfers_nothing(tmp_path, capsys):
    runner = FakeRunner(stdout=remote_listing("/hpc/base", ["profile.txt"]))
    trf.main(["fetch", "-H", "hpc", "-r", "/hpc/base", "-l", str(tmp_path),
              "--dry_run", "--no_fail"], runner=runner)
    assert runner.rsyncs() == []
    assert "profile.txt" in capsys.readouterr().out


### push_db

def make_local(tmp_path, names):
    for n in names:
        path = tmp_path / n
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("x")
    return tmp_path


DB_FILES_19 = ["Pthr_GO_19.0.tsv", "Pthr_GO_19.0_filtered.tsv",
               "inputforGOClassification.tsv", "goparentchild.tsv"]


def test_push_db_sends_only_the_db_load_files(tmp_path):
    make_local(tmp_path, DB_FILES_19 + ["go.json", "profile.txt", "go.obo"])
    runner = FakeRunner()
    trf.main(["push_db", "-H", "db", "-r", "/pgres_data/data/", "-l", str(tmp_path)],
             runner=runner)
    sent = [os.path.basename(c[-2]) for c in runner.rsyncs()]
    assert sorted(sent) == sorted(DB_FILES_19)


def test_push_db_targets_the_load_dir_on_the_db_host(tmp_path):
    make_local(tmp_path, DB_FILES_19)
    runner = FakeRunner()
    trf.main(["push_db", "-H", "db", "-r", "/pgres_data/data/", "-l", str(tmp_path)],
             runner=runner)
    assert all(c[-1].startswith("db:") for c in runner.rsyncs())
    assert all("/pgres_data/data" in c[-1] for c in runner.rsyncs())


def test_push_db_gunzips_remotely_only_for_gz_files(tmp_path):
    """The COPY statements read a plain .tsv, so a pushed .gz has to be expanded there."""
    make_local(tmp_path, ["Pthr_GO_19.0.tsv", "Pthr_GO_19.0_filtered.tsv.gz",
                          "inputforGOClassification.tsv", "goparentchild.tsv"])
    runner = FakeRunner()
    trf.main(["push_db", "-H", "db", "-r", "/pgres_data/data/", "-l", str(tmp_path)],
             runner=runner)
    gunzips = [c[2] for c in runner.sshes() if "gunzip" in c[2]]
    assert len(gunzips) == 1
    assert "Pthr_GO_19.0_filtered.tsv.gz" in gunzips[0]


def test_push_db_prefers_the_gz_variant_to_save_wire(tmp_path):
    make_local(tmp_path, DB_FILES_19 + ["Pthr_GO_19.0_filtered.tsv.gz"])
    runner = FakeRunner()
    trf.main(["push_db", "-H", "db", "-r", "/pgres_data/data/", "-l", str(tmp_path)],
             runner=runner)
    sent = [os.path.basename(c[-2]) for c in runner.rsyncs()]
    assert "Pthr_GO_19.0_filtered.tsv.gz" in sent
    assert "Pthr_GO_19.0_filtered.tsv" not in sent


def test_push_db_exits_nonzero_when_a_load_file_is_missing_locally(tmp_path, capsys):
    make_local(tmp_path, ["Pthr_GO_19.0.tsv"])
    runner = FakeRunner()
    exit_code = trf.main(["push_db", "-H", "db", "-r", "/pgres_data/data/", "-l", str(tmp_path)],
                         runner=runner)
    assert exit_code != 0
    assert "goparentchild.tsv" in capsys.readouterr().out


### push_gafs

def test_push_gafs_sends_the_release_tarball(tmp_path):
    tarball = tmp_path / "2026-08-18_release.tar.gz"
    tarball.write_text("x")
    runner = FakeRunner()
    trf.main(["push_gafs", "-H", "ftp", "-r", "/srv/ftp/paint/19.0/2026-08-18",
              "-a", str(tarball)], runner=runner)
    assert [c[-2] for c in runner.rsyncs()] == [str(tarball)]
    assert runner.rsyncs()[0][-1].startswith("ftp:")


def test_push_gafs_makes_the_destination_directory(tmp_path):
    tarball = tmp_path / "r.tar.gz"
    tarball.write_text("x")
    runner = FakeRunner()
    trf.main(["push_gafs", "-H", "ftp", "-r", "/srv/ftp/paint/19.0/2026-08-18",
              "-a", str(tarball)], runner=runner)
    assert any("mkdir -p" in c[2] for c in runner.sshes())


def test_push_gafs_unpacks_remotely_when_asked(tmp_path):
    """The FTP server serves the tree, so strip the tarball's top-level dir."""
    tarball = tmp_path / "r.tar.gz"
    tarball.write_text("x")
    runner = FakeRunner()
    trf.main(["push_gafs", "-H", "ftp", "-r", "/srv/ftp/paint/19.0/2026-08-18",
              "-a", str(tarball), "--unpack"], runner=runner)
    untar = next(c[2] for c in runner.sshes() if "tar -xzf" in c[2])
    assert "--strip-components=1" in untar
    assert "/srv/ftp/paint/19.0/2026-08-18" in untar


def test_push_gafs_does_not_unpack_for_hpc_archival(tmp_path):
    tarball = tmp_path / "r.tar.gz"
    tarball.write_text("x")
    runner = FakeRunner()
    trf.main(["push_gafs", "-H", "hpc", "-r", "/archive/paint", "-a", str(tarball)],
             runner=runner)
    assert not any("tar -xzf" in c[2] for c in runner.sshes())


def test_push_gafs_exits_nonzero_and_names_the_producer_when_the_tarball_is_absent(tmp_path, capsys):
    runner = FakeRunner()
    exit_code = trf.main(["push_gafs", "-H", "ftp", "-r", "/srv/ftp",
                          "-a", str(tmp_path / "nope.tar.gz")], runner=runner)
    assert exit_code != 0
    assert "release_tarball" in capsys.readouterr().out


### shared behaviour

def test_a_failing_transfer_stops_the_run_and_exits_nonzero(tmp_path, capsys):
    make_local(tmp_path, DB_FILES_19)
    runner = FakeRunner()
    runner.returncode = 255
    exit_code = trf.main(["push_db", "-H", "db", "-r", "/pgres_data/data/", "-l", str(tmp_path)],
                         runner=runner)
    assert exit_code != 0
    assert len(runner.rsyncs()) == 1, "should not keep pushing after a failure"


### fetch_plan: the summary and the rsync must agree on the local destination

def entry_for(path, panther_version="19.0"):
    return next(f for f in trf.release_files(panther_version) if f.path == path)


def test_fetch_plan_lands_a_gz_source_as_a_gz_local_file():
    """The summary used to promise a plain .tsv while rsync wrote the .gz."""
    files = [entry_for("Pthr_GO_19.0_filtered.tsv")]
    plan, missing = trf.fetch_plan(files, "/b", "/local",
                                   {"/b/Pthr_GO_19.0_filtered.tsv.gz"})
    assert missing == []
    assert [(remote, local) for _, remote, local in plan] == [
        ("/b/Pthr_GO_19.0_filtered.tsv.gz", "/local/Pthr_GO_19.0_filtered.tsv.gz")
    ]


def test_fetch_plan_keeps_the_resources_subdirectory():
    files = [entry_for("resources/complex_terms.tsv")]
    plan, _ = trf.fetch_plan(files, "/b", "/local", {"/b/resources/complex_terms.tsv"})
    assert plan[0][2] == "/local/resources/complex_terms.tsv"


def test_fetch_plan_reports_what_is_absent():
    files = [entry_for("go.json"), entry_for("profile.txt")]
    plan, missing = trf.fetch_plan(files, "/b", "/local", {"/b/go.json"})
    assert [f.path for f in missing] == ["profile.txt"]
    assert len(plan) == 1


def test_fetch_summary_and_transfer_name_the_same_destination(tmp_path, capsys):
    runner = FakeRunner(stdout=remote_listing("/hpc/base", ["Pthr_GO_19.0_filtered.tsv.gz"]))
    trf.main(["fetch", "-H", "hpc", "-r", "/hpc/base", "-l", str(tmp_path), "--no_fail"],
             runner=runner)
    out = capsys.readouterr().out
    destination = os.path.join(str(tmp_path), "Pthr_GO_19.0_filtered.tsv.gz")
    assert f"->  {destination}" in out
    assert destination == runner.rsyncs()[0][-1]


### .tar.gz archives
#
# Completed releases keep Pthr_GO as a real tar.gz (2026-05-06 and 2026-08-10 both do), while
# 2026-07-27 has a plain .tsv and a plain .tsv.gz. All three forms occur, and a .tar.gz name
# also ends in ".gz" - so gunzip would leave a .tsv.tar file that no COPY statement can read.

def test_fetch_probes_for_tar_gz_as_well():
    runner = FakeRunner(stdout="")
    trf.main(["fetch", "-H", "hpc", "-r", "/b", "-l", "/tmp/x", "--no_fail"], runner=runner)
    probe = runner.sshes()[0][2]
    assert "/b/Pthr_GO_19.0.tsv.tar.gz" in probe
    assert "/b/Pthr_GO_19.0.tsv.gz" in probe
    assert "/b/Pthr_GO_19.0.tsv " in probe + " "


def test_fetch_plan_takes_tar_gz_when_it_is_the_only_compressed_form():
    files = [entry_for("Pthr_GO_19.0_filtered.tsv")]
    plan, _ = trf.fetch_plan(files, "/b", "/local", {"/b/Pthr_GO_19.0_filtered.tsv.tar.gz"})
    assert plan[0][1] == "/b/Pthr_GO_19.0_filtered.tsv.tar.gz"
    assert plan[0][2] == "/local/Pthr_GO_19.0_filtered.tsv.tar.gz"


def test_fetch_plan_prefers_compressed_over_the_plain_file():
    files = [entry_for("Pthr_GO_19.0.tsv")]
    plan, _ = trf.fetch_plan(files, "/b", "/local",
                             {"/b/Pthr_GO_19.0.tsv", "/b/Pthr_GO_19.0.tsv.tar.gz"})
    assert plan[0][1] == "/b/Pthr_GO_19.0.tsv.tar.gz"


def test_fetch_plan_precedence_is_deterministic_when_every_form_exists():
    """gz before tar.gz: gunzip is simpler and consumes the archive."""
    files = [entry_for("Pthr_GO_19.0.tsv")]
    plan, _ = trf.fetch_plan(files, "/b", "/local", {
        "/b/Pthr_GO_19.0.tsv", "/b/Pthr_GO_19.0.tsv.gz", "/b/Pthr_GO_19.0.tsv.tar.gz"})
    assert plan[0][1] == "/b/Pthr_GO_19.0.tsv.gz"


def test_fetch_skips_wire_compression_for_a_tar_gz(tmp_path):
    runner = FakeRunner(stdout=remote_listing("/b", ["Pthr_GO_19.0.tsv.tar.gz"]))
    trf.main(["fetch", "-H", "hpc", "-r", "/b", "-l", str(tmp_path), "--no_fail"], runner=runner)
    assert "-z" not in runner.rsyncs()[0]


def test_push_db_chooses_a_local_tar_gz_variant(tmp_path):
    make_local(tmp_path, ["Pthr_GO_19.0.tsv.tar.gz", "Pthr_GO_19.0_filtered.tsv.tar.gz",
                          "inputforGOClassification.tsv", "goparentchild.tsv"])
    runner = FakeRunner()
    assert trf.main(["push_db", "-H", "db", "-r", "/load/", "-l", str(tmp_path)],
                    runner=runner) == 0
    sent = [os.path.basename(c[-2]) for c in runner.rsyncs()]
    assert "Pthr_GO_19.0.tsv.tar.gz" in sent


def test_push_db_untars_a_tar_gz_into_the_plain_name_copy_expects(tmp_path):
    make_local(tmp_path, ["Pthr_GO_19.0.tsv.tar.gz", "Pthr_GO_19.0_filtered.tsv",
                          "inputforGOClassification.tsv", "goparentchild.tsv"])
    runner = FakeRunner()
    trf.main(["push_db", "-H", "db", "-r", "/load/", "-l", str(tmp_path)], runner=runner)
    expansion = next(c[2] for c in runner.sshes() if "tar" in c[2])
    assert "tar -xzOf" in expansion
    assert expansion.rstrip().endswith("/load/Pthr_GO_19.0.tsv")


def test_push_db_never_gunzips_a_tar_gz(tmp_path):
    """gunzip -f on a .tsv.tar.gz yields a .tsv.tar that COPY cannot read."""
    make_local(tmp_path, ["Pthr_GO_19.0.tsv.tar.gz", "Pthr_GO_19.0_filtered.tsv",
                          "inputforGOClassification.tsv", "goparentchild.tsv"])
    runner = FakeRunner()
    trf.main(["push_db", "-H", "db", "-r", "/load/", "-l", str(tmp_path)], runner=runner)
    assert not any("gunzip" in c[2] for c in runner.sshes())


def test_push_db_still_gunzips_a_plain_gz(tmp_path):
    make_local(tmp_path, ["Pthr_GO_19.0.tsv", "Pthr_GO_19.0_filtered.tsv.gz",
                          "inputforGOClassification.tsv", "goparentchild.tsv"])
    runner = FakeRunner()
    trf.main(["push_db", "-H", "db", "-r", "/load/", "-l", str(tmp_path)], runner=runner)
    gunzip = next(c[2] for c in runner.sshes() if "gunzip" in c[2])
    assert "Pthr_GO_19.0_filtered.tsv.gz" in gunzip
    assert not any("tar" in c[2] for c in runner.sshes())


def test_push_db_handles_both_archive_forms_in_one_run(tmp_path):
    make_local(tmp_path, ["Pthr_GO_19.0.tsv.tar.gz", "Pthr_GO_19.0_filtered.tsv.gz",
                          "inputforGOClassification.tsv", "goparentchild.tsv"])
    runner = FakeRunner()
    trf.main(["push_db", "-H", "db", "-r", "/load/", "-l", str(tmp_path)], runner=runner)
    remote_cmds = " ".join(c[2] for c in runner.sshes())
    assert "tar -xzOf" in remote_cmds and "gunzip -f" in remote_cmds
