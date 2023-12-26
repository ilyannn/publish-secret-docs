#!/usr/bin/env python
"""
Convert plan files into Markdown files with a code block
"""

from glob import glob
from os.path import isfile, join, splitext
from textwrap import dedent

import click

from redact import ProcessingMessage, create_and_write

LANGUAGE_BY_EXTENSION = {
    "yml": "yaml",
    "yaml": "yaml",
    "tf": "tcl",
}


@click.command()
@click.argument("in_dir")
@click.argument("out_dir")
def redact(in_dir, out_dir):
    """Convert all files into markdown files

    :param in_dir: Input directory path (relative to current working directory)
    :param out_dir: Output directory path (will be created if it does not exist)
    """

    for filename in glob("**/*", recursive=True, root_dir=in_dir):
        fullname = join(in_dir, filename)
        if isfile(fullname):
            with ProcessingMessage(filename):
                _, split2 = splitext(filename)
                extension = split2.lower()[1:] if split2 and split2[0] == "." else ""

                with open(fullname, "rt") as input_stream:
                    text = input_stream.read()

                if extension == "md":
                    md_file = filename
                    out_text = text
                else:
                    lang = LANGUAGE_BY_EXTENSION.get(extension, extension)
                    md_file = filename + ".md"
                    out_text = "\n".join(
                        [
                            "+++",
                            "  title = '" + filename + "'",
                            "+++",
                            "```" + lang,
                            text,
                            "```",
                        ]
                    )

                create_and_write(out_dir, md_file, out_text)


if __name__ == "__main__":
    redact()
