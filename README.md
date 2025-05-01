# pfsConfig Redaction Tool

A tool to mask information unrelated to a specific proposal ID in `pfsConfig`.

The following values are masked as follows when a fiber is assigned for a `SCIENCE` object, i.e., `targetType == 1`, `proposalId != "N/A"` and `proposalId` is not the specific proposal under processed.

| Keyword                    |            Mask value |
|----------------------------|----------------------:|
| `catId`                    |                  9000 |
| `tract`                    |                     0 |
| `patch`                    |                 `0,0` |
| `objId`                    | Hashed 64-bit integer |
| `ra`                       |                   0.0 |
| `dec`                      |                   0.0 |
| `pmRa`                     |                   0.0 |
| `pmDec`                    |                   0.0 |
| `parallax`                 |                1.0e-7 |
| `proposalId`               |              `masked` |
| `obCode`                   |              `masked` |
| `{fiber,psf,total}Flux`    |           list of NaN |
| `{fiber,psf,total}FluxErr` |           list of NaN |
| `filterNames`              |        list of `none` |

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

import os

from astropy.io import fits
from pfs.datamodel import PfsConfig

import pfsconfig_redaction

indir = "tmp"
outdir = "tmp"
input_file = "PFSF12361000.fits"

frame_id_orig = fits.getheader(os.path.join(indir, input_file), ext=0)["FRAMEID"]
pfs_config = PfsConfig.readFits(os.path.join(indir, input_file))

redacted_pfsconfigs = pfsconfig_redaction.redact(
    pfs_config,
    cpfsf_id0=0,
    secret_salt="my_secret_salt",
)
```

The returned `redacted_pfsconfigs` is a list of `RedactedPfsConfig` objects, which has `proposal_id`, `cpfsf_id`, and `pfs_config` attributes. The `proposal_id` and `cpfsf_id` attributes are the proposal_id and cpfsf_id to be delivered. The `pfs_config` attribute is a `PfsConfig` object with the information masked.
