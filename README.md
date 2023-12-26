# Publish Secret Documents

We implement the following Python scripts to convert YAML and Terraform manifests into a format suitable for [Zola static site generator](https://www.getzola.org/):

### [redact.py](redact.py)

This script is used to redact sensitive data. It selects only the config files that are referenced in `.md` files and applies some heuristics to find passwords and token values and replace them with `REDACTED`. This is best considered as just one of the layers in the Swiss cheese defence model.

### [to_markdown.py](to_markdown.py)

This script is used to convert all files into Markdown. It enables syntax highlighting and adds a title to manifest files.
