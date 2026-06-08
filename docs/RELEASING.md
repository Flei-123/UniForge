# Releasing & Updates

How the in-addon updater works and how to publish a new version so users get
the "Update available" prompt automatically.

## How updates reach users (already built)

The Blender addon ([uniforge/update/](../blender_addon/uniforge/update/)):

- On every Blender start it checks GitHub Releases in the background.
- A **Check for Updates** button lives in Preferences.
- If a newer release exists, an **Update available: vX.Y.Z** box appears in the
  N-Panel and Preferences with a **Download & Install Update** button that
  downloads the release zip and installs it over the running addon (the user
  restarts Blender to finish).

It only needs a place to publish versions: a **public GitHub repository** whose
Releases the addon reads via `api.github.com/repos/<repo>/releases/latest`.

## One-time setup

1. Create a public GitHub repo, e.g. `fleitec/uniforge`.
2. Set the repo in [update/core.py](../blender_addon/uniforge/update/core.py):
   `GITHUB_REPO = "fleitec/uniforge"`.
3. Push the project (local dev and published releases coexist — you keep
   working locally and only publish finished builds).

> You do not have to open-source everything to use this — but the Blender addon
> is GPL, so its source is redistributable anyway. A private repo would require
> shipping a token in the addon (not recommended); a public repo is simplest.

## Publishing a new version

1. Bump the version tuple in
   [uniforge/__init__.py](../blender_addon/uniforge/__init__.py) `bl_info`
   (e.g. `(1, 1, 0)`).
2. Build the zip:
   ```
   python scripts/build_release.py
   ```
   → `dist/UniForge-1.1.0.zip`
3. On GitHub: **Releases → Draft a new release**, tag `v1.1.0`, and **attach
   the zip** as a release asset. Publish.

That's it. Every user's addon sees the new tag, shows the prompt, and installs
on click. (The updater compares tags numerically, tolerating a leading `v` and
pre-release suffixes, and prefers an attached `.zip` asset over the source
zipball.)

## Unity plugin updates

The Unity side updates through the Package Manager, not the addon:

- **Git URL (recommended for direct distribution):** users add
  `"com.fleitec.uniforge": "https://github.com/fleitec/uniforge.git?path=/unity_plugin/com.fleitec.uniforge#v1.1.0"`
  to their `Packages/manifest.json`. Bumping the `#tag` and re-resolving pulls
  the update; UPM also shows updates for Git packages.
- **Unity Asset Store:** the store handles update notifications for buyers.

Keep the Blender `bl_info` version, the Unity `package.json` version, and the
GitHub release tag in lock-step.
