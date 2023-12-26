#!/usr/bin/env python
"""
Redact the sensitive info from the YAML and TF config files.
"""
from collections import deque
from glob import glob
from os import makedirs
from os.path import abspath, commonpath, dirname, join, relpath, splitext
from typing import Optional
from urllib.parse import urlparse

import click
import tiktoken
from inflect import engine
from marko import Markdown
from marko.element import Element
from marko.inline import Link

SECRET_LENGTH_REQUIREMENT = 10

plural = engine().no
tokenizer = tiktoken.encoding_for_model("gpt-4")


def token_length(value):
    return len(tokenizer.encode(value))


def as_file_destination(dest: str, source: str, base: str) -> Optional[str]:
    """
    Compute a destination path to a file, relative to a base directory.

    :param dest: The destination path to convert, e.g. '../some/path/to/file'
    :param source: The source path to derive the base directory from, e.g. '/home/folder'
    :param base: The base directory for all the directories, e.g. '/home'
    :return: The converted file path relative to `base`, or None if the file is outside the base directory.
    """
    try:
        url = urlparse(dest)
        if url.scheme:
            return None
    except ValueError:
        pass

    resolved = abspath(join(base, dirname(source), dest))
    if commonpath([resolved, base]) != base:
        return None

    return relpath(resolved, base)


def secret_minimum_requirement(value):
    """
    :param value: The value to check for the secret minimum requirement.
    :return: True if the value meets the secret minimum requirement, False otherwise.
    """
    return any(x.isdigit() for x in value) and len(value) >= SECRET_LENGTH_REQUIREMENT


def value_looks_random(value):
    """
    Check if the given value appears to be random using the tokenization algorithm.

    :param value: The value to be checked.
    :return: True if the value appears to be random, False otherwise.
    """
    if " " in value:
        return any(value_looks_random(part) for part in value.split(" "))

    return (
        secret_minimum_requirement(value)
        and len(tokenizer.encode(value)) > (len(value) * 0.6)
        or len(tokenizer.encode(value)) > (len(value) * 0.45) > 12
    )


def is_a_secret(key, value):
    """We define secret as:
    - a sequence with a digit
    - of length at least 10
    - which is either
       - hinted with the key containing one of two strings
       - or is part of the value separated by the whitespace which looks random for ChatGPT tokenizer
    """
    key = key.lower()
    return (
        secret_minimum_requirement(value)
        if "token" in key or "password" in key
        else value_looks_random(value)
    )


def redact_text(text, file_ext) -> (str, int):
    """
    :param text: The input text to be redacted. It can be a multiline string.
    :param file_ext: The file extension specifying the format of the input text (e.g., '.yaml', '.txt').
    :return: A tuple containing the redacted text (str) and the count of redacted lines (int).

    This method iterates through the key/value pairs (according to the rules specific for the given file extension) of
    the input text and redacts anything that looks like sensitive information found in the values with "REDACTED".
    The resulting text is returned along with the count of redacted values.
    """
    count_redacted = 0

    def gen():
        nonlocal count_redacted

        for line in text.splitlines(keepends=True):
            sep = ":" if file_ext == ".yaml" else "="

            if "#" in line and not line.partition("#")[0].strip():
                yield line
                continue

            if sep not in line and "=" in line:
                sep = "="

            if sep not in line and ":" in line:
                sep = ":"

            key, sep_, value = line.partition(sep)
            stripped_value = value.partition("#")[0].strip(" \n\"',")
            if key and sep_ and value and is_a_secret(key, stripped_value):
                yield key + sep_ + (" " if value[0] == " " else "") + "REDACTED" + (
                    "\n" if value[-1] == "\n" else ""
                )
                count_redacted += 1
            else:
                yield line

    out_text = "".join(gen())
    return out_text, count_redacted


def create_and_write(out_dir, filename, text):
    """
    A simple helper to create and write contents to a file.

    :param out_dir: The directory to create the file in.
    :param filename: The name of the file to create.
    :param text: The text to write to the file.
    """
    output_file = join(out_dir, filename)
    makedirs(dirname(output_file), exist_ok=True)
    with open(output_file, "wt") as output_stream:
        output_stream.write(text)


class ProcessingMessage(object):
    """A class for producing nicely formatted "processing xxx... done" messages."""

    def __init__(self, file_name):
        self.file_name = file_name
        self.formatted_file_name = click.style(
            click.format_filename(file_name), "white", bold=True
        )

    def __enter__(self):
        message = f"Processing {self.formatted_file_name}... "
        click.echo(message, nl=False)
        return self

    def __exit__(self, type, value, traceback):
        message = (
            click.style("error", fg="red") if type else click.style("done", "green")
        )
        click.echo(message)


@click.command()
@click.argument("in_dir")
@click.argument("out_dir")
def redact(in_dir, out_dir):
    """Copy markdown and YAML/TF files referenced there, but redact the secrets

    :param in_dir: Input directory path (relative to current working directory)
    :param out_dir: Output directory path (will be created if it does not exist)
    """
    markdown = Markdown()
    referenced_files = set()
    in_dir = abspath(in_dir)
    out_dir = abspath(out_dir)

    for md_file in glob("**/*.md", recursive=True, root_dir=in_dir):
        with ProcessingMessage(md_file):
            found_links = 0
            with open(join(in_dir, md_file), "rt") as input_stream:
                text = input_stream.read()
            document = markdown.parse(text)
            queue = deque([document])
            while queue:
                node: Element = queue.popleft()
                if hasattr(node, "children"):
                    queue.extend(node.children)
                if isinstance(node, Link):
                    if file_dest := as_file_destination(node.dest, md_file, in_dir):
                        found_links += 1
                        referenced_files.add(file_dest)
            click.echo(
                f"found {click.style(plural('link', found_links), 'blue', underline=True)}, ",
                nl=False,
            )
            create_and_write(out_dir, md_file, text)

    for value_file in sorted(referenced_files):
        try:
            with ProcessingMessage(value_file):
                with open(join(in_dir, value_file), "rt") as input_stream:
                    text = input_stream.read()
                out_text, found_secrets = redact_text(text, splitext(value_file)[1])
                click.echo(
                    f"redacted {click.style(plural('secret', found_secrets), reverse=True)}, ",
                    nl=False,
                )
                create_and_write(out_dir, value_file, out_text)
        except FileNotFoundError:
            pass


if __name__ == "__main__":
    redact()
