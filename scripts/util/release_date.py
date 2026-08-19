import json
import re

# The LBL release-date.json has shipped both `{"date": "2024-06-17"}` and the
# unquoted `{date: 2026-06-19}`, the latter of which is not parseable as JSON.
DATE_PATTERN = re.compile(r'"?date"?\s*:\s*"?(\d{4}-\d{2}-\d{2})"?')


def read_release_date(release_date_path):
    """Return the GO release date from a release date file.

    Handles the GOEx `release_date.txt` (bare date on the first line) and the LBL
    `release-date.json`, whether or not that JSON is well-formed.
    """
    with open(release_date_path) as df:
        contents = df.read()

    if release_date_path.endswith(".txt"):
        return contents.splitlines()[0].strip()

    try:
        return json.loads(contents)['date']
    except (json.JSONDecodeError, KeyError):
        match = DATE_PATTERN.search(contents)
        if match is None:
            raise ValueError(f"No release date found in {release_date_path}: {contents[:100]!r}")
        return match.group(1)
