#!/usr/bin/env python3

import argparse
import os

from ..utils import load_design, mask_entries, write_designs


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "pfs_design_identifier",
        help="Input pfsDesign ID (either hex or int (default)) or pfsDesign filename",
    )
    parser.add_argument("--hex", action="store_true", help="Hex string pfsDesign ID")
    parser.add_argument("--file", action="store_true", help="File Input")
    parser.add_argument("-d", "--indir", default=".", help="Input Directory")
    parser.add_argument("-o", "--outdir", default=".", help="Output directory")

    args = parser.parse_args()

    in_design = load_design(
        args.pfs_design_identifier,
        indir=args.indir,
        is_hex=args.hex,
        is_file=args.file,
    )

    out_designs = mask_entries(in_design)

    write_designs(
        out_designs,
        prefix=os.path.splitext(in_design.filename)[0],
        outdir=args.outdir,
    )


if __name__ == "__main__":
    main()
