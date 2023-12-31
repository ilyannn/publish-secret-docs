# Publishing Sensitive Configuration

We implement a couple of Python scripts that convert YAML and Terraform manifests in such a way that they are compatible with the [Zola Static Site Generator](https://www.getzola.org/).

Here are the scripts and information about what they do:

### 1. Redaction: [redact.py](redact.py)

The purpose of the `redact.py` script is to redact sensitive data from our manifest files.

It guarantees that only files referenced in `.md` files will ever be included in the documentation.
Using a set of heuristics, it looks for sensitive information like passwords or tokens and replaces them with `REDACTED`.

It's advised to apply caution when using this method, at best as only a single layer as part of a Swiss cheese defense strategy.

### 2. Conversion to Markdown: [to_markdown.py](to_markdown.py)

The `to_markdown.py` script is used to convert all manifests into Markdown format consumed by Zola.

It activates syntax highlighting for all code and adds a preamble to every file,
thus enhancing their readability and understandability.
