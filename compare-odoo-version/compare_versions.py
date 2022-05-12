import json
import os
import urllib.request
from ast import literal_eval
from pathlib import Path
from typing import Any
from typing import List
from typing import Optional
from typing import Tuple

# NOTE: we expect the `release` key to have this format: `12.0.1.2.3`
# odoo_version.semver

TAG_PREFIX = 'v'
MODULE_NAME = os.getenv('MODULE_NAME')


def get_manifest_path() -> Path:
    module_path = os.getenv('MODULE_PATH')
    if module_path is None:
        module_path = os.environ['GITHUB_WORKSPACE']
    return Path(module_path).resolve().joinpath('__manifest__.py')


def get_current_version_from_manifest(manifest_path: Path) -> Tuple[int, ...]:
    print(manifest_path)
    with open(manifest_path, 'r') as f:
        return tuple(map(int, literal_eval(f.read())['version'].split('.')))


def get_releases_data() -> Any:
    req = urllib.request.Request(f'{os.environ["GITHUB_API_URL"]}/repos/{os.environ["GITHUB_REPOSITORY"]}/releases')
    req.add_header('Accept', 'application/vnd.github.v3+json')
    req.add_header('Authorization', f'Bearer {os.environ["GITHUB_TOKEN"]}')
    with urllib.request.urlopen(req) as f:
        return json.loads(f.read().decode('utf-8'))


def get_latest_release_from_speficic_odoo_version(releases_data: Any, current_version: Tuple[int, ...]) -> str:
    release_string = f'{TAG_PREFIX}{current_version[0]}'
    if MODULE_NAME is not None:
        release_string = f'{MODULE_NAME}-{release_string}'

    existing_releases: List[str] = sorted(
        [item['tag_name'] for item in releases_data if item['tag_name'].startswith(release_string)],
    )
    print(existing_releases)
    if existing_releases:
        print(existing_releases[-1])
        return existing_releases[-1]
    else:
        return ''


def get_new_version(current_version: Tuple[int, ...], latest_release: str) -> Optional[str]:
    new_version = f'{TAG_PREFIX}{".".join(map(str, (i for i in current_version)))}'
    chars_to_clean = TAG_PREFIX
    if MODULE_NAME is not None:
        new_version = f'{MODULE_NAME}-{new_version}'
        chars_to_clean = f'{MODULE_NAME}-{TAG_PREFIX}'

    new_release_flag = False
    if latest_release != '':
        latest_release_tuple = tuple(map(int, latest_release.lower().replace(chars_to_clean, '').split('.')))
        if current_version > latest_release_tuple:
            # if a prior release exists, and it is smaller than the specified on the
            # manifest, create a new release
            new_release_flag = True
    else:
        if current_version > (0, 0, 0, 0, 0):
            # if no prior release exists, and the current is not 0, create a new one
            new_release_flag = True

    if new_release_flag:
        return new_version
    else:
        return None


if __name__ == '__main__':
    manifest_path = get_manifest_path()
    current_version = get_current_version_from_manifest(manifest_path)
    latest_release = get_latest_release_from_speficic_odoo_version(get_releases_data(), current_version)
    new_version = get_new_version(current_version, latest_release)
    if new_version is not None:
        os.system(f'echo "::set-output name=new-version::{new_version}"')
        print('NEW RELEASE!', new_version)
