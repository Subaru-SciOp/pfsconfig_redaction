#!/usr/bin/env python3

import argparse

from .. import MaskedPfsDesign


def main():
    parser = argparse.ArgumentParser(
        description="A command-line script to generate pfsDesign or pfsConfig files for each proposal in the input design or config file"
    )
    parser.add_argument(
        "pfs_design_identifier",
        help="Input pfsDesign ID (either hex or int (default)) or pfsDesign/pfsConfig filename",
    )
    parser.add_argument(
        "--visit", type=int, help="Integer visit ID for pfsConfig (default: None)"
    )
    parser.add_argument(
        "--hex", action="store_true", help="Flag for the hex string input"
    )
    parser.add_argument(
        "--file", action="store_true", help="Flag for the filename input"
    )
    parser.add_argument(
        "-d", "--indir", default=".", help="Input Directory (default: .)"
    )
    parser.add_argument(
        "-o", "--outdir", default=".", help="Output directory (default: .)"
    )

    args = parser.parse_args()

    masked_pfs_design = MaskedPfsDesign(
        args.pfs_design_identifier,
        indir=args.indir,
        outdir=args.outdir,
        is_hex=args.hex,
        is_file=args.file,
        visit=args.visit,
    )
    masked_pfs_design.do_all()


if __name__ == "__main__":
    main()
