#!/usr/bin/env python
"""
Convert all files into Markdown format.

Activates syntax highlighting for all code and add a preamble to every file, including Markdown files.
This is the format consumed by the Zola Static Site Generator.
"""

from glob import glob
from os.path import isfile, join, splitext, basename
from typing import Iterable

import click

from redact import ProcessingMessage, create_and_write

LANGUAGE_BY_EXTENSION = {
    "yml": "yaml",
    "yaml": "yaml",
    "tf": "tcl",
}


def zola_preamble(title) -> Iterable[str]:
    return "+++", f"  title = '{title}'", "+++"


def md_code(lang, text) -> Iterable[str]:
    return f"```{lang}", text, "```"


@click.command()
@click.argument("in_dir")
@click.argument("out_dir")
def redact(in_dir, out_dir):
    """Convert all files into markdown files ready for display with Zola 

    Markdown files get a preamble, while all other files are encoded with a ``` code block.
    
    :param in_dir: Input directory path (relative to current working directory)
    :param out_dir: Output directory path (will be created if it does not exist)
    """

    for filename in glob("**/*", recursive=True, root_dir=in_dir):
        fullname = join(in_dir, filename)
        if isfile(fullname):
            with ProcessingMessage(filename):
                _, split2 = splitext(filename)
                ext = split2.lower()[1:] if split2 and split2[0] == "." else ""

                with open(fullname, "rt") as input_stream:
                    text = input_stream.read()

                if ext == "md":
                    md_file = filename
                    header, *out_lines = text.splitlines()
                    title = header.lstrip("#").strip()
                else:
                    md_file = filename + ".md"
                    out_lines = md_code(LANGUAGE_BY_EXTENSION.get(ext, ext), text)
                    title = basename(filename)

                out_text = "\n".join((*zola_preamble(title), *out_lines))
                create_and_write(out_dir, md_file, out_text)


if __name__ == "__main__":
    redact()
