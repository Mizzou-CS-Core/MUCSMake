import logging

import tomlkit
from tomlkit import document, table, comment, dumps

from .models import Config

_config: Config = None
logger = logging.getLogger(__name__)

CONFIG_FILE = "config.toml"

def prepare_toml_doc():
    doc = document()

    general = table()
    general.add("mucsv2_instance_code", "")
    general.add(comment("Checks for a C header file corresponding to the lab name in the submission."))
    general.add("check_lab_header", True)
    general.add("run_valgrind", True)

    paths = table()
    paths.add("base_path", "/cluster/pixstor/class/")
    paths.add("db_path", "data/(mucs_instance_code).db")
    paths.add("lab_submission_directory", "submissions")
    paths.add("test_files_directory", "data/test_files")
    paths.add(comment("All valid submissions go here within your grader's submission folder."))
    paths.add("valid_dir", ".valid")
    paths.add(comment("All invalid submissions go here within your grader's submission folder."))
    paths.add("invalid_dir", ".invalid")
    paths.add(comment("All invalid submissions go here within your grader's submission folder."))
    paths.add("late_dir", ".late")
    doc['general'] = general
    doc['paths'] = paths

    with open(CONFIG_FILE, 'w') as f:
        _ = f.write(dumps(doc))
    print(f"Created default {CONFIG_FILE}")


def get_config() -> Config:
    if _config is None:
        logger.critical("The config has not been loaded into memory!")
        return None
    return _config


def prepare_config_obj():
    with open(CONFIG_FILE, 'r') as f:
        content = f.read()
    doc = tomlkit.parse(content)
    global _config

    # Extract values from the TOML document
    general = doc.get('general', {})
    paths = doc.get('paths', {})
    canvas = doc.get('canvas', {})

    _config = Config(mucsv2_instance_code=general.get('mucsv2_instance_code'), run_valgrind=general.get('run_valgrind'),
                     base_path=paths.get('base_path'), lab_submission_directory=paths.get('lab_submission_directory'),
                     test_files_directory=paths.get('test_files_directory'), valid_dir=paths.get('valid_dir'),
                     invalid_dir=paths.get('invalid_dir'), db_path=paths.get("db_path"))
