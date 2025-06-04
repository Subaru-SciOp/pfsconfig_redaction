# pfsConfig Redaction Tool

A tool to mask information unrelated to a specific proposal ID in `pfsConfig`.

The following values are masked as follows when a fiber is assigned for a `SCIENCE` object, i.e., `targetType == 1`, `proposalId != "N/A"` and `proposalId` is not the specific proposal under processed.

| Keyword                    | Datatype       |            Mask value |
|----------------------------|----------------|----------------------:|
| `catId`                    | int            |                  9000 |
| `tract`                    | int            |                    -1 |
| `patch`                    | str            |               `-1,-1` |
| `objId`                    | int64          | Hashed 64-bit integer |
| `ra`                       | float          |                   -99 |
| `dec`                      | float          |                   -99 |
| `pmRa`                     | float          |                   0.0 |
| `pmDec`                    | float          |                   0.0 |
| `parallax`                 | float          |                1.0e-7 |
| `proposalId`               | str            |              `masked` |
| `obCode`                   | str            |              `masked` |
| `pfiNominal`               | (float, float) |            (NaN, NaN) |
| `pfiCenter`                | (float, float) |            (NaN, NaN) |
| `{fiber,psf,total}Flux`    | list of float  |           list of NaN |
| `{fiber,psf,total}FluxErr` | list of float  |           list of NaN |
| `filterNames`              | list of str    |        list of `none` |

## Installation

```console
git clone https://github.com/Subaru-SciOp/pfsconfig_redaction.git
cd pfsconfig_redaction
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -r requirements.txt
python3 -m pip install -e .
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

redacted_pfsconfigs = pfsconfig_redaction.redact(
    pfs_config,
    dict_group_id={
        "S24B-EN16": "o24016",
        "S25A-042QN": "o25158",
        "S25A-000QF": "o25103",
        "S25A-034QF": "o25188",
    },
    cpfsf_id0=0,
    secret_salt="my_secret_salt",
)

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
