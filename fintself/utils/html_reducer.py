import os
from bs4 import BeautifulSoup, Comment


def reduce_html(html_content: str) -> str:
    """
    Reduces HTML content by removing script, style, and comment tags,
    and collapsing excessive whitespace.
    """
    soup = BeautifulSoup(html_content, "html.parser")

    # Remove script and style elements
    for script_or_style in soup(["script", "style"]):
        script_or_style.decompose()

    # Remove comments
    for comment in soup.find_all(string=lambda text: isinstance(text, Comment)):
        comment.extract()

    # Get the prettified HTML and then strip extra whitespace from each line
    stripped_text = soup.prettify()
    return "\n".join(
        [line.strip() for line in stripped_text.splitlines() if line.strip()]
    )


def process_debug_html_directory(input_dir: str, output_dir: str):
    """
    Processes all HTML files in the input_dir and saves reduced versions to output_dir.
    """
    os.makedirs(output_dir, exist_ok=True)
    for root, _, files in os.walk(input_dir):
        # Skip if the current directory is the output_dir or a subdirectory of it
        if os.path.commonpath([root, output_dir]) == output_dir and root != input_dir:
            continue

        for file in files:
            if file.endswith(".html"):
                input_filepath = os.path.join(root, file)
                # Construct relative path from input_dir to maintain directory structure
                relative_path_in_input_dir = os.path.relpath(input_filepath, input_dir)
                output_filepath = os.path.join(output_dir, relative_path_in_input_dir)

                # Ensure we don't try to process files already in the output directory
                if os.path.commonpath([input_filepath, output_dir]) == output_dir:
                    continue

                os.makedirs(os.path.dirname(output_filepath), exist_ok=True)

                with open(input_filepath, "r", encoding="utf-8") as f:
                    html_content = f.read()

                reduced_content = reduce_html(html_content)

                with open(output_filepath, "w", encoding="utf-8") as f:
                    f.write(reduced_content)
                print(f"Reduced: {input_filepath} -> {output_filepath}")
