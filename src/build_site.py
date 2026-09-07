"""Prepare static Pages files. Only explicit public deployment metadata is emitted."""
import json
import os
from pathlib import Path
import re
import shutil

ROOT = Path(__file__).resolve().parent.parent


def build_site(root=ROOT):
    repository = os.environ['GITHUB_REPOSITORY']
    branch = os.environ['DEFAULT_BRANCH']
    if not re.fullmatch(r'[A-Za-z0-9-]+/[A-Za-z0-9_.-]+', repository) or not branch:
        raise ValueError('Invalid repository/branch metadata')
    shutil.copytree(root / 'data', root / 'docs/data', dirs_exist_ok=True)
    (root / 'docs/site.json').write_text(json.dumps({
        'repository': repository,
        'default_branch': branch,
    }, indent=2) + '\n', encoding='utf-8')


if __name__ == '__main__':
    build_site()
