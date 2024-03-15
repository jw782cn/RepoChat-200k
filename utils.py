import os
import requests
import csv
import pandas as pd
import zipfile
import fnmatch
from pygments.lexers import guess_lexer_for_filename, TextLexer
from pygments.util import ClassNotFound
import nbformat

def download_repo(repo_url, local_path):
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

            # 解压缩下载的ZIP文件
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(local_repo_path)

            # 删除下载的ZIP文件
            os.remove(zip_path)

            return local_repo_path
        else:
            print(f"Failed to download the repository. Status code: {response.status_code}")
            return None
    except Exception as e:
        print(f"An error occurred: {str(e)}")
        return None
    

def repo_stats(repo_path, csv_path=None):
    if csv_path is None:
        csv_path = os.path.join(repo_path, 'repo_stats.csv')

    # 读取.gitignore文件
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

            # 检查文件是否匹配.gitignore中的忽略规则
            if any(fnmatch.fnmatch(rel_path, pattern) for pattern in ignore_patterns):
                continue

            if file.endswith('.ipynb'):
                # 处理Jupyter Notebook文件
                with open(file_path, 'r', encoding='utf-8') as f:
                    notebook = nbformat.read(f, as_version=4)
                    content = nbformat.writes(notebook)
                language = 'Jupyter Notebook'
            else:
                # 处理其他文件
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()

                # 使用pygments识别文件的编程语言
                try:
                    lexer = guess_lexer_for_filename(file_path, content)
                    language = lexer.name
                except ClassNotFound:
                    language = None

                if language is not None and isinstance(lexer, TextLexer):
                    language = None

            data.append({
                'file_content': content,
                'language': language,
                'line_count': len(content.split('\n')),
                'file_size': os.path.getsize(file_path),
                'file_name': file,
                'file_path': rel_path,
                'token_count': None,  # 留空,之后由其他函数填充
                'file_hash': None  # 留空,之后由其他函数填充
            })

    df = pd.DataFrame(data)
    df.to_csv(csv_path, index=False)

    return df, csv_path


def language_percentage(csv_path):
    df = pd.read_csv(csv_path)

    # 检查language列是否为空
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
    

def filter_files(csv_path, file_paths):
    df = pd.read_csv(csv_path)
    df['file_path'] = df['file_path'].str.replace(os.sep, '/')
    file_paths = [path.lower() for path in file_paths]
    conditions = []
    for path in file_paths:
        if path.endswith('/'):
            conditions.append(df['file_path'].str.lower().str.startswith(path))
        else:
            conditions.append(df['file_path'].str.lower() == path)
    final_condition = conditions[0]
    for condition in conditions[1:]:
        final_condition |= condition
    filtered_df = df[final_condition]
    return filtered_df


