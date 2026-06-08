"""Version comparison and GitHub Releases lookup — no bpy, unit-testable.

The addon polls the GitHub Releases API for the latest published release and
compares its tag (e.g. ``v1.1.0``) against the running addon version. Uses only
the Python standard library (urllib) so the addon keeps its "no external
dependencies" guarantee.
"""

import json
import re
import urllib.error
import urllib.request

# Set this to the public repository that hosts UniForge releases.
GITHUB_REPO = "Flei-123/UniForge"

_RELEASES_LATEST = "https://api.github.com/repos/{repo}/releases/latest"
_USER_AGENT = "UniForge-Updater"
_VERSION_RE = re.compile(r"\d+")


def parse_version(text):
    """Parse a version string/tag into a comparable int tuple.

    Tolerant of a leading 'v', pre-release suffixes, and missing components::

        "v1.2.3"     -> (1, 2, 3)
        "1.10"       -> (1, 10)
        "v2.0.0-beta"-> (2, 0, 0)
    """
    if text is None:
        return ()
    # Stop at the first pre-release/build separator so "1.0.0-beta" -> (1,0,0).
    core = re.split(r"[-+ ]", str(text).strip().lstrip("vV"), maxsplit=1)[0]
    return tuple(int(n) for n in _VERSION_RE.findall(core))


def is_newer(latest, current):
    """True if version tuple/string ``latest`` is strictly newer than ``current``."""
    lv = latest if isinstance(latest, tuple) else parse_version(latest)
    cv = current if isinstance(current, tuple) else parse_version(current)
    return _padded(lv, cv) > _padded(cv, lv)


def _padded(a, b):
    """Right-pad the shorter tuple with zeros so (1,0) == (1,0,0)."""
    return a + (0,) * (len(b) - len(a))


def select_download_url(release):
    """Pick the best download URL from a GitHub release JSON object.

    Prefers an uploaded ``.zip`` asset (the packaged addon); falls back to the
    auto-generated source ``zipball_url``.
    """
    for asset in release.get("assets", []) or []:
        name = (asset.get("name") or "").lower()
        if name.endswith(".zip"):
            return asset.get("browser_download_url")
    return release.get("zipball_url")


def fetch_latest_release(repo=GITHUB_REPO, timeout=10):
    """Return the parsed 'latest release' JSON, or None on any failure."""
    url = _RELEASES_LATEST.format(repo=repo)
    request = urllib.request.Request(url, headers={"User-Agent": _USER_AGENT})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8"))
    except (urllib.error.URLError, ValueError, TimeoutError, OSError):
        return None


def check_for_update(current_version, repo=GITHUB_REPO, timeout=10):
    """Check GitHub for a newer release.

    Returns a dict::

        {
          "available": bool,
          "current":   "1.0.0",
          "latest":    "1.1.0" or None,
          "url":       download URL or None,
          "notes":     release body or "",
          "error":     None or a short message,
        }
    """
    current = (
        current_version
        if isinstance(current_version, tuple)
        else parse_version(current_version)
    )
    result = {
        "available": False,
        "current": ".".join(str(n) for n in current),
        "latest": None,
        "url": None,
        "notes": "",
        "error": None,
    }

    release = fetch_latest_release(repo=repo, timeout=timeout)
    if release is None:
        result["error"] = "Could not reach the update server."
        return result

    tag = release.get("tag_name") or release.get("name")
    latest = parse_version(tag)
    if not latest:
        result["error"] = "No valid release tag found."
        return result

    result["latest"] = ".".join(str(n) for n in latest)
    result["notes"] = (release.get("body") or "").strip()
    if is_newer(latest, current):
        result["available"] = True
        result["url"] = select_download_url(release)
    return result
