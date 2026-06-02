"""ambientCG API client — search CC0 materials and resolve download links.

Pure standard library (urllib) so it stays importable and testable without
Blender. ambientCG assets are CC0: free to use and ship in any project.
"""

import json
import shutil
import urllib.error
import urllib.parse
import urllib.request

_API = "https://ambientcg.com/api/v2/full_json"
_USER_AGENT = "UniForge-MaterialBrowser"


def search(query="", limit=30, sort="Popular", timeout=15):
    """Return a list of material dicts: {id, preview, resolutions}.

    ``resolutions`` maps an attribute label (e.g. "1K-JPG") to a download URL.
    Returns [] on any network/parse failure.
    """
    params = {
        "type": "Material",
        "include": "downloadData,imageData",
        "limit": limit,
        "sort": sort,
    }
    if query:
        params["q"] = query

    url = _API + "?" + urllib.parse.urlencode(params)
    request = urllib.request.Request(url, headers={"User-Agent": _USER_AGENT})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            data = json.loads(response.read().decode("utf-8"))
    except (urllib.error.URLError, ValueError, TimeoutError, OSError):
        return []

    results = []
    for asset in data.get("foundAssets", []) or []:
        downloads = (
            asset.get("downloadFolders", {})
            .get("default", {})
            .get("downloadFiletypeCategories", {})
            .get("zip", {})
            .get("downloads", [])
        )
        resolutions = {
            d.get("attribute"): d.get("downloadLink")
            for d in downloads
            if d.get("attribute") and d.get("downloadLink")
        }
        preview = asset.get("previewImage") or {}
        results.append(
            {
                "id": asset.get("assetId"),
                "preview": preview.get("256-PNG") or preview.get("128-PNG"),
                "resolutions": resolutions,
            }
        )
    return results


def pick_download(resolutions, resolution="1K"):
    """Choose a download URL for the requested resolution, preferring JPG."""
    for attribute in (f"{resolution}-JPG", f"{resolution}-PNG"):
        if attribute in resolutions:
            return resolutions[attribute]
    return next(iter(resolutions.values()), None)


def download(url, dest_path, timeout=120):
    """Download ``url`` to ``dest_path``; raises on failure."""
    request = urllib.request.Request(url, headers={"User-Agent": _USER_AGENT})
    with urllib.request.urlopen(request, timeout=timeout) as response, open(dest_path, "wb") as out:
        shutil.copyfileobj(response, out)
