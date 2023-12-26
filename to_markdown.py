#!/usr/bin/env python
"""
Convert plan files into Markdown files with a code block
"""

from glob import glob
from os.path import isfile, join, splitext

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
                _, extension = splitext(filename)
                with open(fullname, "rt") as input_stream:
                    text = input_stream.read()

                extension = (
                    extension.lower()[1:] if extension and extension[0] == "." else ""
                )
                if extension == "md":
                    md_file = filename
                    out_text = text
                else:
                    md_file = filename + ".md"
                    out_text = (
                        "```"
                        + LANGUAGE_BY_EXTENSION.get(extension, extension)
                        + "\n"
                        + text
                        + "```"
                    )

                create_and_write(out_dir, md_file, out_text)


if __name__ == "__main__":
    redact()
