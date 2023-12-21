#!/usr/bin/env python
from collections import deque
from glob import glob
from os import makedirs
from os.path import join, relpath, dirname, commonpath, abspath, splitext
from typing import Optional
from urllib.parse import urlparse

import click
import tiktoken
from inflect import engine
from marko import Markdown
from marko.element import Element
from marko.inline import Link

plural = engine().no
tokenizer = tiktoken.encoding_for_model('gpt-4')


def as_file_destination(dest: str, source: str, base: str) -> Optional[str]:
    """Returns a file path if this is a link to file, HTTP(S) links and similar return None"""
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


assert as_file_destination("http://example.com", "/home/me/folder", "/home/me") is None
assert as_file_destination("./file.txt", "/home/me/folder/file.md", "/home/me") == "folder/file.txt"
assert as_file_destination("subdir/file.txt", "/home/me/folder/file.md", "/home/me") == "folder/subdir/file.txt"
assert as_file_destination("../file.txt", "/home/me/folder/file.md", "/home/me") == "file.txt"
assert as_file_destination("../../file.txt", "/home/me/folder/file.md", "/home/me") is None


def secret_minimum_requirement(value):
    return any(x.isdigit() for x in value) and len(value) >= 10


def value_looks_random(value):
    if ' ' in value:
        return any(value_looks_random(part) for part in value.split(' '))

    return secret_minimum_requirement(value) and len(tokenizer.encode(value)) > (len(value) * 0.6) or len(tokenizer.encode(value)) > (len(value) * 0.45) > 12


def is_a_secret(key, value):
    """We define secret as:
       - a sequence with a digit
       - of length at least 10
       - which is either
          - hinted with the key containing one of two strings
          - or is part of the value separated by the whitespace which looks random for ChatGPT tokenizer
       """
    key = key.lower()
    return secret_minimum_requirement(value) if 'token' in key or 'password' in key else value_looks_random(value)


assert is_a_secret('my_password', 'jshd_K176!')
assert is_a_secret('API_TOKEN', 'nBJGKTKB68Gvbsdf6aKJGKUTusdbfkIUjsdfvk')
assert is_a_secret('value', 'my_email nBJGKTKB68Gvbsdf6aKJGKUTusdbfkIUjsdfvk')
assert not is_a_secret('value', 'my_email postmater@my.site')
assert not is_a_secret('use_password_auth', 'false')
assert not is_a_secret('tokenizer', 'default')
assert not is_a_secret('webserver', 'route-53.example.com')
assert is_a_secret("value", "qFWAPxEkKkqZ9i9QLad50Nk5mZ1DcxFifUj4")


def redact_text(text, file_ext) -> (str, int):
    count_redacted = 0

    def gen():
        nonlocal count_redacted

        for line in text.splitlines(keepends=True):
            sep = ':' if file_ext == '.yaml' else '='

            if '#' in line and not line.partition('#')[0].strip():
                yield line
                continue

            if sep not in line and '=' in line:
                sep = '='

            if sep not in line and ':' in line:
                sep = ':'

            key, sep_, value = line.partition(sep)
            stripped_value = value.partition('#')[0].strip(' \n\"\',')
            if key and sep_ and value and is_a_secret(key, stripped_value):
                yield key + sep_ + (' ' if value[0] == ' ' else '') + 'REDACTED' + ('\n' if value[-1] == '\n' else '')
                count_redacted += 1
            else:
                yield line

    out_text = "".join(gen())
    return out_text, count_redacted


assert redact_text("safe_flag: true", '.yaml') == ("safe_flag: true", 0)
assert redact_text("password: jasghDSGF2346", '.yaml') == ("password: REDACTED", 1)
assert redact_text("- --zone=hwer5uy6528hHJG", '.yaml') == ("- --zone=REDACTED", 1)
assert redact_text('value: "kjhds76HJfjkhnf7868HJKGfhagdsJHGJ"', '.yaml') == ('value: REDACTED', 1)
assert redact_text('password: jhajksdjk&T*^%ghvsd324GHhd', '.tf') == ('password: REDACTED', 1)

def create_and_write(out_dir, filename, text):
    output_file = join(out_dir, filename)
    makedirs(dirname(output_file), exist_ok=True)
    with open(output_file, "wt") as output_stream:
        output_stream.write(text)


class ProcessingMessage(object):
    def __init__(self, file_name):
        self.file_name = file_name
        self.formatted_file_name = click.style(click.format_filename(file_name), "white", bold=True)

    def __enter__(self):
        message = f"Processing {self.formatted_file_name}... "
        click.echo(message, nl=False)
        return self

    def __exit__(self, type, value, traceback):
        message = click.style("error", fg="red") if type else click.style("done", "green")
        click.echo(message)


@click.command()
@click.argument('in_dir')
@click.argument('out_dir')
def redact(in_dir, out_dir):
    """Copy markdown and YAML/TF files referenced there, but redact the secrets"""
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
            click.echo(f"found {click.style(plural('link', found_links), 'blue', underline=True)}, ", nl=False)
            create_and_write(out_dir, md_file, text)

    for value_file in sorted(referenced_files):
        try:
            with ProcessingMessage(value_file):
                with open(join(in_dir, value_file), "rt") as input_stream:
                    text = input_stream.read()
                out_text, found_secrets = redact_text(text, splitext(value_file)[1])
                click.echo(f"redacted {click.style(plural('secret', found_secrets), reverse=True)}, ", nl=False)
                create_and_write(out_dir, value_file, out_text)
        except FileNotFoundError:
            pass


if __name__ == '__main__':
    redact()
