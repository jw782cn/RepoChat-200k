import os
import requests
import pandas as pd
import zipfile
import fnmatch
from pygments.lexers import guess_lexer_for_filename, TextLexer
from pygments.util import ClassNotFound
import nbformat
import json
from token_count import num_tokens_from_string


def download_repo(repo_url, local_path):
    '''Download a GitHub repository as a ZIP file and extract it to a local directory.'''
    try:
        repo_name = repo_url.split('/')[-1]
        local_repo_path = os.path.join(local_path, repo_name)
        os.makedirs(local_repo_path, exist_ok=True)

        zip_url = f"{repo_url}/archive/master.zip"
        response = requests.get(zip_url)

        if response.status_code == 200:
            zip_path = os.path.join(local_path, f"{repo_name}.zip")
            with open(zip_path, 'wb') as f:
                f.write(response.content)

            # unzip the file
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(local_repo_path)

            # remove the zip file
            os.remove(zip_path)

            return local_repo_path
        else:
            print(
                f"Failed to download the repository. Status code: {response.status_code}")
            return None
    except Exception as e:
        print(f"An error occurred: {str(e)}")
        return None


def convert_ipynb_to_text(ipynb_content):
    '''Convert a Jupyter Notebook to a text string.'''
    notebook = json.loads(ipynb_content)
    text = ""
    for cell in notebook['cells']:
        if cell['cell_type'] == 'markdown':
            text += ''.join(cell['source']) + '\n\n'
        elif cell['cell_type'] == 'code':
            text += '```python\n'
            text += ''.join(cell['source']) + '\n'
            text += '```\n\n'
            if len(cell['outputs']) > 0:
                text += '<output>\n'
                for output in cell['outputs']:
                    if output['output_type'] == 'stream':
                        text += ''.join(output['text']) + '\n'
                    elif output['output_type'] == 'execute_result':
                        text += ''.join(output['data'].get('text/plain', '')) + '\n'
                    elif output['output_type'] == 'error':
                        text += ''.join(output['traceback']) + '\n'
                text += '</output>\n\n'

    return text.strip()


def repo_stats(repo_path, csv_path=None):
    '''Generate statistics for a local GitHub repository.'''
    if csv_path is None:
        csv_path = os.path.join(repo_path, 'repo_stats.csv')

    # read the .gitignore file
    gitignore_path = os.path.join(repo_path, '.gitignore')
    ignore_patterns = []
    if os.path.exists(gitignore_path):
        with open(gitignore_path, 'r') as f:
            ignore_patterns = f.read().splitlines()

    data = []
    for root, dirs, files in os.walk(repo_path):
        for file in files:
            file_path = os.path.join(root, file)
            rel_path = os.path.relpath(file_path, repo_path)

            # check if the file is in the .gitignore
            if any(fnmatch.fnmatch(rel_path, pattern) for pattern in ignore_patterns):
                continue

            if file.endswith('.ipynb'):
                # Jupyter Notebook files
                with open(file_path, 'r', encoding='utf-8') as f:
                    notebook = nbformat.read(f, as_version=4)
                    content = nbformat.writes(notebook)
                language = 'Jupyter Notebook'

                token_count_content = convert_ipynb_to_text(content)
                token_count = num_tokens_from_string(token_count_content)
            else:
                # other files
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()

                # use Pygments to guess the language
                try:
                    lexer = guess_lexer_for_filename(file_path, content)
                    language = lexer.name
                except ClassNotFound:
                    language = None

                if language is not None and isinstance(lexer, TextLexer):
                    language = None
                token_count = num_tokens_from_string(content)

            data.append({
                'file_content': content,
                'language': language,
                'line_count': len(content.split('\n')),
                'file_size': os.path.getsize(file_path),
                'file_name': file,
                'file_path': rel_path,
                'token_count': token_count,
                'file_summary': None
            })

    df = pd.DataFrame(data)
    df.to_csv(csv_path, index=False)

    return df, csv_path


def filter_files(csv_path, file_paths, language=None):
    '''Filter files in a CSV file based on file paths and language.'''
    df = pd.read_csv(csv_path)
    df['file_path'] = df['file_path'].str.replace(os.sep, '/')
    file_paths = [path.lower() for path in file_paths]

    conditions = []

    # file path conditions
    for path in file_paths:
        if path.endswith('/'):
            conditions.append(df['file_path'].str.lower().str.startswith(path))
        else:
            conditions.append(df['file_path'].str.lower() == path)

    # language condition
    if language is not None:
        conditions.append(df['language'] == language)

    # combine conditions
    final_condition = conditions[0]
    for condition in conditions[1:]:
        final_condition &= condition

    filtered_df = df[final_condition]
    return filtered_df


def language_percentage(csv_path):
    '''Calculate the percentage of lines of code for each language in a CSV file.'''
    df = pd.read_csv(csv_path)

    # check if the 'language' column is empty
    if df['language'].isna().all():
        print("Warning: 'language' column is empty. Please make sure the 'language' column is populated.")
        return None

    language_counts = df.groupby('language')['line_count'].sum()
    total_lines = language_counts.sum()

    if total_lines == 0:
        print("Warning: Total line count is zero. Cannot calculate language percentage.")
        return None

    language_percentage = language_counts / total_lines * 100
    return language_percentage


def print_directory_structure(repo_path):
    '''Print the directory structure of a local GitHub repository.'''
    directory_structure = {}

    for root, dirs, files in os.walk(repo_path):
        for file in files:
            file_path = os.path.relpath(os.path.join(root, file), repo_path)
            parts = file_path.split(os.sep)
            current_level = directory_structure

            for part in parts:
                if part not in current_level:
                    current_level[part] = {}
                current_level = current_level[part]

    def print_structure(structure, level=0):
        for key, value in structure.items():
            print('  ' * level + '- ' + key)
            print_structure(value, level + 1)

    print_structure(directory_structure)


def preprocess_dataframe(df, limit=None, concat_method='xml', include_directory=True, metadata_list=None):
    '''Preprocess a DataFrame to generate a string representation of the data.'''
    result = ''

    if include_directory:
        directory_structure = {}
        for _, row in df.iterrows():
            file_path = row['file_path']
            parts = file_path.split('/')
            current_level = directory_structure
            for part in parts:
                if part not in current_level:
                    current_level[part] = {}
                current_level = current_level[part]

        def flatten_directory(structure, prefix=''):
            flattened = []
            for key, value in structure.items():
                flattened.append(prefix + key)
                flattened.extend(flatten_directory(value, prefix + '  '))
            return flattened

        directory_lines = flatten_directory(directory_structure)
        result += 'Directory Structure:\n' + \
            '\n'.join(directory_lines) + '\n\n'

    for _, row in df.iterrows():
        r = result
        result += '\n\n' + '=' * 10 + '\n\n'
        content = row['file_content']
        if row['language'] == 'Jupyter Notebook':
            content = convert_ipynb_to_text(content)

        if metadata_list:
            metadata = [str(row[col]) for col in metadata_list]
        else:
            metadata = ""

        if concat_method == 'xml':
            result += f'<file name="{row["file_path"]}">\n'
            if metadata:
                result += f'<metadata>{", ".join(metadata)}</metadata>\n'
            result += f'<content>\n{content}\n</content>\n'
            result += '</file>'
        else:
            result += f'File: {row["file_path"]}\n'
            if metadata:
                result += f'Metadata: {", ".join(metadata)}\n'
            result += f'Content:\n{content}'
        result += '\n\n' + '=' * 10 + '\n\n'
        if limit and num_tokens_from_string(result) > limit:
            result = r
            break

    return result.strip()


def get_filtered_files(repo_path, file_paths, language=None, limit=None, concat_method='xml', include_directory=True, metadata_list=None):
    csv_path = os.path.join(repo_path, "repo_stats.csv")
    filtered_files = filter_files(csv_path, file_paths, language=language)
    output = preprocess_dataframe(filtered_files, limit=limit,  concat_method=concat_method,
                                  include_directory=include_directory, metadata_list=metadata_list)
    return output
