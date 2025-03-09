#!/usr/bin/env python3
import os
import sys


def create_adoc_content(file_path):
    # Get relative path from project root
    rel_path = file_path
    if rel_path.startswith("./"):
        rel_path = rel_path[2:]

    # Get filename without extension
    filename = os.path.basename(file_path)
    name_without_ext = os.path.splitext(filename)[0]

    # Read the Python file content
    with open(file_path, "r") as f:
        code_content = f.read()

    # Create AsciiDoc content
    content = f"""= {name_without_ext}


== Documentation

TODO: Add documentation for this module

== Location
[source]
----
./{rel_path}
----
== Code

[source,python]
----
{code_content}
----
"""
    return content


def main():
    # Create docs directory if it doesn't exist
    if not os.path.exists("docs"):
        os.makedirs("docs")

    # Find all Python files
    for root, _, files in os.walk("."):
        for file in files:
            if file.endswith(".py") and file != "create_docs.py":
                py_path = os.path.join(root, file)

                # Create corresponding docs directory structure
                doc_dir = os.path.join(
                    "docs", root[2:] if root.startswith("./") else root
                )
                if not os.path.exists(doc_dir):
                    os.makedirs(doc_dir)

                # Create .adoc file path
                adoc_file = os.path.join(doc_dir, os.path.splitext(file)[0] + ".adoc")

                # Generate and write content
                content = create_adoc_content(py_path)
                with open(adoc_file, "w") as f:
                    f.write(content)

                print(f"Created: {adoc_file}")


if __name__ == "__main__":
    main()
