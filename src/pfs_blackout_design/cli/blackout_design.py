#!/usr/bin/env python3

import argparse

from ..utils import generate_design_per_propid


def main():
    parser = argparse.ArgumentParser(
        description="A command-line script to generate pfsDesign files for each proposal in the input design file"
    )
    parser.add_argument(
        "pfs_design_identifier",
        help="Input pfsDesign ID (either hex or int (default)) or pfsDesign filename",
    )
    parser.add_argument("--hex", action="store_true", help="Hex string pfsDesign ID")
    parser.add_argument("--file", action="store_true", help="File Input")
    parser.add_argument("-d", "--indir", default=".", help="Input Directory")
    parser.add_argument("-o", "--outdir", default=".", help="Output directory")

    args = parser.parse_args()

    generate_design_per_propid(
        args.pfs_design_identifier,
        indir=args.indir,
        outdir=args.outdir,
        is_hex=args.hex,
        is_file=args.file,
    )


if __name__ == "__main__":
    main()
