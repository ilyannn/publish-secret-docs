# Publishing Tools

These tools convert YAML and Terraform manifests into a format suitable for [Zola static site generator](https://www.getzola.org/):

- **[redact.py](redact.py)** select only the config files referenced in `.md` files and redacts the sensitive data
- **[to_markdown.py](to_markdown.py)** converts all files into Markdown, enabling syntax highlighting
