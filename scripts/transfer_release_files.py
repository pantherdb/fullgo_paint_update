"""Move release files between the three machines the pipeline spans.

A firewall blocks the HPC cluster from reaching the DB servers, so the local workstation
relays. Three hops, none of which the Makefile used to automate:

    fetch      cluster BASE_PATH  -> local BASE_PATH   (make fetch_release_files)
    push_db    local BASE_PATH    -> DB server load_dir (make push_db_load_files)
    push_gafs  local release tarball -> file server / HPC archive
               (make push_gafs_to_ftp, make archive_gafs_to_hpc)

The manifest below is the point of the script: it records every file a later step needs
and why, so nobody has to remember the list. Transfers use rsync over ssh, so an
interrupted multi-GB file resumes instead of restarting.
"""

import argparse
import os
import posixpath
import shlex
import subprocess
import sys
from collections import namedtuple

GZ_SUFFIX = ".gz"
TAR_GZ_SUFFIXES = (".tar.gz", ".tgz")
# Search order when picking which form of a file to move. Compressed first: ~8x less wire on
# the multi-GB Pthr_GO files. .gz before .tar.gz because gunzip is simpler and consumes the
# archive. All three forms occur in practice - 2026-05-06 and 2026-08-10 kept Pthr_GO as
# .tsv.tar.gz, 2026-07-27 as a plain .tsv plus a plain .tsv.gz.
# (compare_pthr_go_counts.py searches plain-first instead: reading a local file has no wire to
# save, so decompression is pure cost there.)
TRANSFER_SUFFIXES = (GZ_SUFFIX, ".tar.gz", "")

# path may contain {panther_version}; db_load marks the files a {load_dir} COPY reads.
ReleaseFile = namedtuple("ReleaseFile", ["path", "needed_by", "db_load"])

RELEASE_FILES = (
    ReleaseFile("Pthr_GO_{panther_version}.tsv",
                "panther.goanno_wf COPY (load_raw_go_to_panther)", True),
    ReleaseFile("Pthr_GO_{panther_version}_filtered.tsv",
                "panther_upl.goanno_wf COPY (load_raw_go_to_paint)", True),
    ReleaseFile("inputforGOClassification.tsv",
                "goobo_extract COPY (both schemas)", True),
    ReleaseFile("goparentchild.tsv",
                "goobo_parent_child COPY (both schemas)", True),
    ReleaseFile("profile.txt",
                "GO_VERSION_DATE, GAF_PROFILE, check-profile, *_version.sql", False),
    ReleaseFile("go.json",
                "setup_preupdate_data symlink", False),
    ReleaseFile("goparentchild_isaonly.tsv",
                "setup_preupdate_data symlink", False),
    ReleaseFile("resources/complex_terms.tsv",
                "setup_preupdate_data prerequisite + symlink", False),
    ReleaseFile("go.obo",
                "ad-hoc ontology reference (no Makefile consumer)", False),
)

CommandResult = namedtuple("CommandResult", ["returncode", "stdout"])


def is_tar_archive(path):
    """A .tsv.tar.gz also ends in .gz, so gunzip would leave an unreadable .tsv.tar."""
    return path.endswith(TAR_GZ_SUFFIXES)


def is_compressed(path):
    return path.endswith(GZ_SUFFIX) or is_tar_archive(path)


def subprocess_runner(cmd, capture=False):
    """The real command runner. Tests inject a recording stand-in instead."""
    if capture:
        finished = subprocess.run(cmd, capture_output=True, text=True)
        return CommandResult(finished.returncode, finished.stdout)
    return CommandResult(subprocess.call(cmd), "")


def release_files(panther_version):
    return tuple(f._replace(path=f.path.format(panther_version=panther_version))
                 for f in RELEASE_FILES)


def db_load_files(panther_version):
    return tuple(f for f in release_files(panther_version) if f.db_load)


def rsync_command(source, dest):
    """rsync over ssh, resumable. -z is wasted CPU on an already-gzipped file."""
    flags = ["-av", "--partial", "--progress"]
    if not is_compressed(source):
        flags.append("-z")
    return ["rsync"] + flags + [source, dest]


def remote_probe_command(host, remote_base, files):
    """One ssh call listing every candidate; ls prints the hits and errors on the misses."""
    candidates = []
    for release_file in files:
        remote = posixpath.join(remote_base, release_file.path)
        candidates.extend(remote + suffix for suffix in TRANSFER_SUFFIXES)
    listing = " ".join(shlex.quote(c) for c in candidates)
    return ["ssh", host, f"ls -1d -- {listing} 2>/dev/null"]


def fetch_plan(files, remote_base, local_base, existing):
    """Decide, per manifest file, what to pull and where it lands.

    Prefers the .gz sibling - ~8x less wire for the multi-GB Pthr_GO files - and mirrors the
    remote name locally, so a fetched .gz stays a .gz rather than being mislabelled.
    Returns (plan, missing) where plan holds (release_file, remote_path, local_path).
    """
    plan, missing = [], []
    for release_file in files:
        plain = posixpath.join(remote_base, release_file.path)
        remote = next((plain + s for s in TRANSFER_SUFFIXES if plain + s in existing), None)
        if remote is None:
            missing.append(release_file)
            continue
        local = os.path.join(local_base, os.path.dirname(release_file.path),
                             posixpath.basename(remote))
        plan.append((release_file, remote, local))
    return plan, missing


def choose_local_variant(local_base, release_file):
    """The local counterpart of choose_remote_variants; None when neither form is present."""
    plain = os.path.join(local_base, release_file.path)
    return next((plain + s for s in TRANSFER_SUFFIXES if os.path.isfile(plain + s)), None)


def remote_expand_command(host, remote_archive, remote_dir, plain_name):
    """Leave the plain .tsv a COPY statement reads, whatever archive form arrived."""
    if is_tar_archive(remote_archive):
        # -O ignores any directory structure inside the archive, so the single member lands at
        # exactly the name COPY looks for rather than under a dated subdirectory.
        target = posixpath.join(remote_dir, plain_name)
        return ["ssh", host,
                f"tar -xzOf {shlex.quote(remote_archive)} > {shlex.quote(target)}"]
    return ["ssh", host, f"gunzip -f {shlex.quote(remote_archive)}"]


def report_missing(missing, where):
    print(f"\nERROR: {len(missing)} required file(s) not found {where}:")
    for release_file in missing:
        print(f"  {release_file.path}\n      needed by: {release_file.needed_by}")


def run_all(commands, runner, dry_run):
    """Run in order, stopping at the first failure - a partial transfer is worse than none."""
    for cmd in commands:
        if dry_run:
            print("  DRY RUN: " + " ".join(cmd))
            continue
        print("  " + " ".join(cmd))
        result = runner(cmd)
        if result.returncode != 0:
            print(f"\nERROR: command failed with exit {result.returncode}: {' '.join(cmd)}")
            return False
    return True


def fetch(args, runner):
    files = release_files(args.panther_version)
    probe = remote_probe_command(args.host, args.remote_path, files)
    # Read-only, so it runs even under --dry_run: we cannot report the plan without it.
    print(f"Probing {args.host}:{args.remote_path} for the {len(files)} manifest files:")
    print("  " + " ".join(probe))
    existing = {line.strip() for line in runner(probe, capture=True).stdout.splitlines()
                if line.strip()}

    plan, missing = fetch_plan(files, args.remote_path, args.local_path, existing)
    print(f"\n{len(plan)} of {len(files)} manifest files found on {args.host}:")
    for _, remote, local in plan:
        print(f"  {remote}  ->  {local}")
    if missing:
        report_missing(missing, f"on {args.host}:{args.remote_path}")

    commands = []
    for _, remote, local in plan:
        if not args.dry_run:
            os.makedirs(os.path.dirname(os.path.abspath(local)), exist_ok=True)
        commands.append(rsync_command(f"{args.host}:{remote}", local))

    print(f"\nTransferring {len(commands)} file(s) to {args.local_path}:")
    if not run_all(commands, runner, args.dry_run):
        return 1
    return 1 if missing and not args.no_fail else 0


def push_db(args, runner):
    files = db_load_files(args.panther_version)
    found, missing = [], []
    for release_file in files:
        local = choose_local_variant(args.local_path, release_file)
        (found.append((release_file, local)) if local else missing.append(release_file))

    print(f"{len(found)} of {len(files)} DB load files found in {args.local_path}:")
    for _, local in found:
        print(f"  {local}  ->  {args.host}:{args.remote_path}")
    if missing:
        report_missing(missing, f"in {args.local_path}")
        if not args.no_fail:
            return 1

    commands = []
    for release_file, local in found:
        remote = posixpath.join(args.remote_path, os.path.basename(local))
        commands.append(rsync_command(local, f"{args.host}:{shlex.quote(args.remote_path)}"))
        if is_compressed(local):
            # COPY reads a plain .tsv, so expand it there rather than on the wire.
            commands.append(remote_expand_command(
                args.host, remote, args.remote_path, os.path.basename(release_file.path)))

    print(f"\nPushing to {args.host}:{args.remote_path}:")
    return 0 if run_all(commands, runner, args.dry_run) else 1


def push_gafs(args, runner):
    if not os.path.isfile(args.artifact):
        print(f"ERROR: release tarball not found: {args.artifact}")
        print("Run 'make release_tarball' first to build it.")
        return 1

    remote_artifact = posixpath.join(args.remote_path, os.path.basename(args.artifact))
    commands = [
        ["ssh", args.host, f"mkdir -p {shlex.quote(args.remote_path)}"],
        rsync_command(args.artifact, f"{args.host}:{shlex.quote(args.remote_path)}"),
    ]
    if args.unpack:
        # The file server serves the tree, so drop the tarball's dated top-level directory.
        commands.append(["ssh", args.host,
                         f"tar -xzf {shlex.quote(remote_artifact)} --strip-components=1 "
                         f"-C {shlex.quote(args.remote_path)}"])

    print(f"Pushing {args.artifact} to {args.host}:{args.remote_path}"
          f"{' and unpacking' if args.unpack else ''}:")
    return 0 if run_all(commands, runner, args.dry_run) else 1


def build_parser():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    subparsers = parser.add_subparsers(dest="command", required=True)

    def add_common(subparser, needs_local=True):
        subparser.add_argument('-H', '--host', required=True, help="Destination or source host")
        subparser.add_argument('-r', '--remote_path', required=True,
                               help="Path on that host (BASE_PATH, load_dir, or target dir)")
        if needs_local:
            subparser.add_argument('-l', '--local_path', required=True,
                                   help="Local release BASE_PATH")
        subparser.add_argument('-p', '--panther_version', default="19.0",
                               help="Fills {panther_version} in the manifest (default 19.0)")
        subparser.add_argument('--dry_run', action='store_true',
                               help="Print every command without transferring anything")
        subparser.add_argument('--no_fail', action='store_true',
                               help="Exit 0 even when a manifest file is missing")

    add_common(subparsers.add_parser('fetch', help="Cluster BASE_PATH -> local BASE_PATH"))
    add_common(subparsers.add_parser('push_db', help="Local BASE_PATH -> DB server load_dir"))
    gafs = subparsers.add_parser('push_gafs', help="Release tarball -> file server or archive")
    add_common(gafs, needs_local=False)
    gafs.add_argument('-a', '--artifact', required=True,
                      help="Release tarball built by 'make release_tarball'")
    gafs.add_argument('--unpack', action='store_true',
                      help="Untar remotely into remote_path, stripping the top-level dir")
    return parser


def main(argv=None, runner=subprocess_runner):
    args = build_parser().parse_args(argv)
    return {"fetch": fetch, "push_db": push_db, "push_gafs": push_gafs}[args.command](args, runner)


if __name__ == "__main__":
    sys.exit(main())
