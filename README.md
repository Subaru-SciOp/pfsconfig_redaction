# pfsConfig Redaction Tool

A tool to mask information unrelated to a specific proposal ID in `pfsConfig`.

## `SCIENCE` objects

The following values are masked as follows when a fiber is assigned for a `SCIENCE` object, i.e., `targetType == 1`, `proposalId != "N/A"` and `proposalId` is not the specific proposal being processed.

| Keyword                    | Datatype       |     Mask value |
|----------------------------|----------------|---------------:|
| `tract`                    | int            |             -1 |
| `patch`                    | str            |        `-1,-1` |
| `ra`                       | float          |            -99 |
| `dec`                      | float          |            -99 |
| `catId`                    | int            |           9000 |
| `objId`                    | int64          |     `-fiberId` |
| `targetType`               | int            |             12 |
| `pmRa`                     | float          |            0.0 |
| `pmDec`                    | float          |            0.0 |
| `parallax`                 | float          |         1.0e-7 |
| `proposalId`               | str            |       `masked` |
| `obCode`                   | str            |       `masked` |
| `pfiNominal`               | (float, float) |     (NaN, NaN) |
| `pfiCenter`                | (float, float) |     (NaN, NaN) |
| `{fiber,psf,total}Flux`    | list of float  |    list of NaN |
| `{fiber,psf,total}FluxErr` | list of float  |    list of NaN |
| `filterNames`              | list of str    | list of `none` |

## `FLUXSTD` objects duplicated as `SCIENCE` targets

A star can be observed as a flux standard while also being a `SCIENCE` target of an
open-use program. Such a fiber appears with `targetType == 2` (`FLUXSTD`) but carries the
`proposalId` and `obCode` of that program, which must not be disclosed to the other PIs.

When a fiber is assigned for a `FLUXSTD` object, i.e., `targetType == 2`, `proposalId != "N/A"`
and `proposalId` is not the specific proposal being processed, only the proposal association
is removed.

| Keyword      | Datatype | Mask value |
|--------------|----------|-----------:|
| `proposalId` | str      |      `N/A` |
| `obCode`     | str      |      `N/A` |

Everything else is **kept as is** — in particular `catId`, `objId`, `ra`, `dec`, `targetType`,
the flux values and `filterNames` — because this information is required to use the object as
a flux standard in the downstream calibration.

For the PI of the proposal being processed, these fibers are left completely untouched, so the
`proposalId` and `obCode` of the duplicated flux standards are preserved. Ordinary flux
standards (`proposalId == "N/A"`) are never masked.

## Installation

**Note**: It is highly recommended to use a virtual environment to avoid conflicts with system packages.

### Standard Installation

```console
git clone https://github.com/Subaru-SciOp/pfsconfig_redaction.git
cd pfsconfig_redaction

# Create and activate virtual environment (recommended)
python3 -m venv .venv
source .venv/bin/activate

# Install the package
pip install .
```

### Development Installation

For development purposes, install in editable mode:

```console
git clone https://github.com/Subaru-SciOp/pfsconfig_redaction.git
cd pfsconfig_redaction

# Create and activate virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install in editable mode
pip install -e .
```

### Using uv (Recommended)

If you have [uv](https://docs.astral.sh/uv/) installed (automatically manages virtual environments):

```console
git clone https://github.com/Subaru-SciOp/pfsconfig_redaction.git
cd pfsconfig_redaction
uv sync
```

Dependency versions are pinned in `uv.lock`, which is committed to the repository. To
update the lockfile to the latest versions allowed by `pyproject.toml` and sync your
environment to it:

```console
uv sync --upgrade
```

Commit the updated `uv.lock` so CI and other contributors pick up the same versions.

### Legacy Installation (if needed)

For environments without uv:

```console
git clone https://github.com/Subaru-SciOp/pfsconfig_redaction.git
cd pfsconfig_redaction
pip install .
```

## Usage

```python
from pathlib import Path

from pfs.datamodel import PfsConfig
import pfsconfig_redaction

indir = Path("tmp")
outdir = Path("tmp")
input_file = "PFSF12361000.fits"

pfs_config = PfsConfig.readFits(indir / input_file)

redacted_pfsconfigs = pfsconfig_redaction.redact(pfs_config)

for i, redacted_pfsconfig in enumerate(redacted_pfsconfigs):
    # Skip if proposal_id is "N/A"
    if redacted_pfsconfig.proposal_id == "N/A":
        continue

    proposal_id = redacted_pfsconfig.proposal_id

    # Save the redacted PfsConfig to a FITS file
    redacted_pfsconfig.pfs_config.writeFits(
        outdir / f"redacted_PFSF12361000_{proposal_id}.fits"
    )
```

The returned `redacted_pfsconfigs` is a list of `RedactedPfsConfig` objects, which has `proposal_id` and `pfs_config` attributes. The `proposal_id` attribute is the proposal_id to be delivered. The `pfs_config` attribute is a `PfsConfig` object with the information masked.
