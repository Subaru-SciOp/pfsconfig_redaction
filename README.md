# Blackout pfsDesign

## Installation

```
git clone https://github.com/monodera/pfs_blackout_design.git
cd pfs_blackout_design
python3 -m pip install -e .
```

## Usage

```
$ pfs_blackout_design -h
usage: pfs_blackout_design [-h] [--hex] [--file] [-d INDIR] [-o OUTDIR] pfs_design_identifier

A command-line script to generate pfsDesign files for each proposal in the input design file

positional arguments:
  pfs_design_identifier
                        Input pfsDesign ID (either hex or int (default)) or pfsDesign filename

optional arguments:
  -h, --help            show this help message and exit
  --hex                 Hex string pfsDesign ID
  --file                File Input
  -d INDIR, --indir INDIR
                        Input Directory
  -o OUTDIR, --outdir OUTDIR
                        Output directory
```

### Example

This example read a `pfsDesign` file with the `pfsDesignId` of `5734893949501672337` from the `./tmp/examples` directory and save `pfsDesign` files containing only the information on fibers with a relevant proposal ID and calibration fibers under `./tmp/examples`.
```
$ pfs_blackout_design 5734893949501672337 -d ./tmp/examples --o tmp/examples/
```

The above command will generate the following files in `./tmp/examples`.

```
pfsDesign-0x4f966fa98c958b91_S22A-EN16.fits
pfsDesign-0x4f966fa98c958b91_S23A-QN900.fits
pfsDesign-0x4f966fa98c958b91_S23A-QN901.fits
pfsDesign-0x4f966fa98c958b91_S23A-QN902.fits
pfsDesign-0x4f966fa98c958b91_S23A-QN903.fits
```

You can also tell the `pfsDesignId` by a hex string or filename. The following two commands are equivalent to the example above.

```
# By a hex string
$ pfs_blackout_design 0x4f966fa98c958b91 -d ./tmp/examples -o ./tmp/examples --hex

# By a filename
$ pfs_blackout_design pfsDesign-0x4f966fa98c958b91.fits -d ./tmp/examples -o ./tmp/examples --file
```

## Call from a Python script

The following example is equialent to the command-line client example shown above.

```python
from pfs_blackout_design import MaskedPfsDesign

masked_pfs_design = MaskedPfsDesign("pfsDesign-0x4f966fa98c958b91.fits", indir="./tmp/examples/", outdir="./tmp/examples/", is_file=True)
masked_pfs_design.do_all()
```
