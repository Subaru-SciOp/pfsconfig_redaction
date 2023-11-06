# Blackout pfsDesign

A tool to mask information unrelated to a specific proposal ID in `pfsDesign` and `pfsConfig` files.

The following values are masked as follows.


| Keyword                    |     Mask value |
|----------------------------|---------------:|
| `catId`                    |             -1 |
| `catId`                    |             -1 |
| `tract`                    |              0 |
| `patch`                    |          `0,0` |
| `objId`                    |             -1 |
| `ra`                       |            0.0 |
| `dec`                      |            0.0 |
| `pmRa`                     |            0.0 |
| `pmDec`                    |            0.0 |
| `parallax`                 |         1.0e-8 |
| `proposalId`               |       `masked` |
| `obCode`                   |       `masked` |
| `{fiber,psf,total}Flux`    |    list of NaN |
| `{fiber,psf,total}FluxErr` |    list of NaN |
| `filterNames`              | list of `none` |

- `(catId, objId)=(-1, -1)` is allowed to duplicate. If there are any issues on DRP, please let us know.

## Installation

```sh
git clone https://github.com/monodera/pfs_blackout_design.git
cd pfs_blackout_design
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -r requirements.txt
python3 -m pip install -e .
```

## Usage

```sh
$ pfs_blackout_design -h
usage: pfs_blackout_design [-h] [--visit VISIT] [--hex] [--file] [-d INDIR] [-o OUTDIR] pfs_design_identifier

A command-line script to generate pfsDesign or pfsConfig files for each proposal in the input design or config file

positional arguments:
  pfs_design_identifier
                        Input pfsDesign ID (either hex or int (default)) or pfsDesign/pfsConfig filename

optional arguments:
  -h, --help            show this help message and exit
  --visit VISIT         Integer visit ID for pfsConfig (default: None)
  --hex                 Flag for the hex string input
  --file                Flag for the filename input
  -d INDIR, --indir INDIR
                        Input Directory (default: .)
  -o OUTDIR, --outdir OUTDIR
                        Output directory (default: .)
```

### Example

This example read a `pfsDesign` file with the `pfsDesignId` of `5734893949501672337` from the `./tmp/examples` directory and save `pfsDesign` files containing only the information on fibers with a relevant proposal ID and calibration fibers under `./tmp/examples`.

```shell
$ pfs_blackout_design 5734893949501672337 -d ./tmp/examples -o tmp/examples/
```

The above command will generate the following files in `./tmp/examples`.

```text
pfsDesign-0x4f966fa98c958b91_S22A-EN16.fits
pfsDesign-0x4f966fa98c958b91_S23A-QN900.fits
pfsDesign-0x4f966fa98c958b91_S23A-QN901.fits
pfsDesign-0x4f966fa98c958b91_S23A-QN902.fits
pfsDesign-0x4f966fa98c958b91_S23A-QN903.fits
```

You can work on a `pfsConfig` file by supplying a `visit` parameter as follows.

```sh
$ pfs_blackout_design 5734893949501672337 -d ./tmp/examples -o tmp/examples/ --visit 1
```

The above example reads `pfsConfig-0x4f966fa98c958b91-000001.fits` in the `./tmp/examples/` directory and outputs the following files.

```text
pfsConfig-0x4f966fa98c958b91-000001_S22A-EN16.fits
pfsConfig-0x4f966fa98c958b91-000001_S23A-QN900.fits
pfsConfig-0x4f966fa98c958b91-000001_S23A-QN901.fits
pfsConfig-0x4f966fa98c958b91-000001_S23A-QN902.fits
pfsConfig-0x4f966fa98c958b91-000001_S23A-QN903.fits
```

You can also tell the `pfsDesignId` by a hex string or filename. The following two commands are equivalent to the example above.

```sh
# By a hex string
$ pfs_blackout_design 0x4f966fa98c958b91 -d ./tmp/examples -o ./tmp/examples --hex
$ pfs_blackout_design 0x4f966fa98c958b91 -d ./tmp/examples -o ./tmp/examples --hex --visit 1

# By a filename
$ pfs_blackout_design pfsDesign-0x4f966fa98c958b91.fits -d ./tmp/examples -o ./tmp/examples --file
$ pfs_blackout_design pfsConfig-0x4f966fa98c958b91-000001.fits -d ./tmp/examples -o ./tmp/examples --file
```

## Call from a Python script

The following example is equivalent to the command-line client example shown above.

```python
from pfs_blackout_design import MaskedPfsDesign

masked_pfs_design = MaskedPfsDesign(
    "pfsDesign-0x4f966fa98c958b91.fits",
    indir="./tmp/examples/",
    outdir="./tmp/examples/",
    is_file=True,
)
masked_pfs_design.do_all()
```
