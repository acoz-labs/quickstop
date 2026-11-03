import argparse

from .label import render


def main(argv=None):
    parser = argparse.ArgumentParser(prog='labelmaker')
    parser.add_argument('name')
    parser.add_argument('address')
    args = parser.parse_args(argv)
    print(render(args.name, args.address))
