# pfsConfig Redaction Tool

A tool to mask information unrelated to a specific proposal ID in `pfsConfig`.

The following values are masked as follows when a fiber is assigned for a `SCIENCE` object, i.e., `targetType == 1`, `proposalId != "N/A"` and `proposalId` is not the specific proposal under processed.

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

### Legacy Installation (if needed)

For environments requiring explicit requirements.txt:

```console
git clone https://github.com/Subaru-SciOp/pfsconfig_redaction.git
cd pfsconfig_redaction
pip install -r requirements.txt
pip install .
```

## Usage

```python
from pathlib import Path

from astropy.io import fits
from pfs.datamodel import PfsConfig

import pfsconfig_redaction

indir = Path("tmp")
outdir = Path("tmp")
input_file = "PFSF12361000.fits"

frame_id_orig = fits.getheader(indir / input_file, ext=0)["FRAMEID"]
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

The returned `redacted_pfsconfigs` is a list of `RedactedPfsConfig` objects, which has `proposal_id`, `cpfsf_id`, and `pfs_config` attributes. The `proposal_id` and `cpfsf_id` attributes are the proposal_id and cpfsf_id to be delivered. The `pfs_config` attribute is a `PfsConfig` object with the information masked.
