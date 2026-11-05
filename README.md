# NetApp Volume Utility

A desktop GUI for the daily grind of storage administration: create a volume, create a LUN, map it, see what is mapped. Built for NetApp ONTAP clusters, Python + PySide6, about 2,100 lines.

## Why it exists

Provisioning storage through the ONTAP web UI is slow, and vendor support keeps pointing admins at the CLI anyway. The CLI is powerful but unforgiving: a `volume create` is one long line with eight flags, and a single forgotten flag quietly gives you a volume with snapshots enabled, the wrong security style or no autosize policy. Nobody notices until a LUN runs out of space three months later.

This tool keeps all the "strict" parameters in one config and shows four plain forms instead. The user types a name and a size; the command is assembled by code from values that were checked first. If the input does not match the documented rules, nothing is sent to the storage at all.

## What it does

- **Create Volume**: name, size, aggregate, QoS policy.
- **Create LUN**: name, size, ostype. A checkbox repeats the name and size from the volume tab, because in practice they almost always match.
- **Map LUN**: volume, LUN, igroup, LUN ID. The igroup list is pulled from the cluster and stays editable.
- **Show**: LUNs with their mappings, and the LUN ID for a given igroup.
- **Live SSH console**: raw ONTAP output, every command and every answer, visible while it happens.

## What keeps it safe

- **Credentials live only in memory.** They are typed into the login window, used to open an SSH session and never written anywhere.
- **`settings.json` holds UI preferences only**: language, theme, cluster address, checkbox state. No usernames, no passwords.
- **Commands are never typed by hand.** The UI passes values; `ontap_commands.py` builds the string from the strict layer in `app_config.py`.
- **Validation follows the ONTAP documentation, not habit**: a name starts with a Latin letter, continues with letters, digits or underscore, up to 203 characters; a size is a positive integer with a unit. Fractions, zero and negatives are rejected before the command exists.
- **The +3% size quirk is bounded on purpose.** Volumes are created slightly larger than requested (rounded up to a whole GB), and the quirk is applied to `volume create` only. A LUN always gets exactly the size that was entered.

## Architecture

```
src/
  app_config.py      strict parameter layer: vserver, flags, aggregates, QoS, ostypes
  validation.py      name and size rules, straight from the ONTAP docs
  ontap_commands.py  the only place where command strings are assembled
  session.py         connection state
  backend/
    base.py          one interface, success markers, timeouts
    real.py          paramiko SSH to a live cluster
    fake.py          an ONTAP emulator, so the UI can be developed offline
  ui/                login dialog, main window, four tabs, console widget
  i18n.py            Ukrainian, Russian, English
  theme.py           light and dark QSS
```

Two details worth pointing out, because they were real bugs before they were design:

- **No guessing on success.** `volume create` answers with the marker `Successful`, `lun create` with `Created a LUN of size`, and the backend waits for that marker up to 30 seconds. An earlier version used "one second of silence means done", which reported failures on a slow array while the command had actually succeeded.
- **The igroup parser reads the table, not a guess.** Real ONTAP output is two columns (`vserver igroup`) with the name second; the emulator prints one column. Both are handled, and prompt echoes like `cluster::> igroup show` are skipped instead of being mistaken for data.

## Deliberate deviations from the scripts it replaced

The tool began as a Python replacement for two long PowerShell scripts. Two of their behaviours were intentionally not reproduced:

- The originals sent the volume name into `-lun` and the LUN name into `-volume` on mapping. That is a bug, and the ONTAP semantics are unambiguous, so the tool sends them where they belong.
- LUN names follow the same strict rule as volume names, although ONTAP itself allows a few more characters. One rule is easier to keep in your head than two.

## Requirements and running

```
Python 3.12
pip install -r requirements.txt    # PySide6, paramiko
python src/main.py
```

At startup: language, theme, cluster, cluster address, username, password. The address is stored in `~/.netapp_volume_utility/settings.json` so the same build works against any cluster without rebuilding.

A standalone Windows executable can be built with PyInstaller; the entry point is `src/build_main.py`. Logos are embedded as base64, so the result is a single self-contained file. Details in `docs/BUILD.md`.

## What is not in this repository

- **The original PowerShell scripts.** They are the employer's working artefacts, not mine to publish. The Python code is my own.
- **Cluster addresses.** Placeholders are `0.0.0.0`; you enter your own.
- **Internal QA reports and agent scaffolding.** They refer to those scripts and to a private environment.

The detailed Russian specification, the cluster parameter reference and the full changelog are kept as they were written during the work: `docs/SPEC.md`, `config/clusters.md`, `CHANGELOG.md`. They are the honest record of the project, including the bugs and the arguments about them.

## Status

Working and in use: it provisions volumes and LUNs on production clusters, with the fake backend for testing UI changes without touching storage. It is a focused tool, not a framework: four operations done carefully.

## License

MIT.
