import os
import re

def replace_urls_in_hugo_build(build_dir):
    # Define a regex pattern to match URLs leading to folders
    folder_url_pattern = re.compile(r'(href|src)=("|\')([^"\']+/)(["\'#?])')

    for root, _, files in os.walk(build_dir):
        for file in files:
            if file.endswith('.html'):
                file_path = os.path.join(root, file)

                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()

                # Replace folder URLs with index.html URLs
                def replacer(match):
                    url_prefix = match.group(1)  # href or src
                    quote = match.group(2)      # " or '
                    folder_path = match.group(3)  # URL path to folder
                    trailing_char = match.group(4)  # Ending char: " or # or ?

                    # Skip root domain paths
                    if folder_path in ('/', ''):
                        return match.group(0)
                    if '.com' in folder_path and 'gintarasdev.com' not in folder_path:
                        return match.group(0)

                    # Append index.html to folder paths
                    new_url = f"{folder_path}index.html"
                    return f"{url_prefix}={quote}{new_url}{trailing_char}"

                updated_content = folder_url_pattern.sub(replacer, content)

                # Write changes back to the file if modifications were made
                if content != updated_content:
                    with open(file_path, 'w', encoding='utf-8') as f:
                        f.write(updated_content)

if __name__ == "__main__":
    build_dir = "public"  # Adjust this to your Hugo build directory
    replace_urls_in_hugo_build(build_dir)
    print("URL replacements completed.")
