import logging
from pathlib import Path

import tomlkit
from tomlkit import document, table, comment, dumps

from .models import Config

_config: Config = None
logger = logging.getLogger(__name__)

def prepare_toml_doc(mucsv2_instance_code="", check_lab_header=True, run_valgrind=True,
                     base_path="/cluster/pixstor/class", db_path="/data/<mucs_instance_code>.db",
                     lab_submission_directory="/submissions", test_files_directory="/data/test_files",
                     valid_dir=".valid", invalid_dir=".invalid", late_dir=".late", config_path=Path("")):
    doc = document()

    general = table()
    general.add("mucsv2_instance_code", mucsv2_instance_code)
    general.add(comment("Checks for a C header file corresponding to the lab name in the submission."))
    general.add("check_lab_header", check_lab_header)
    general.add("run_valgrind", run_valgrind)

    paths = table()
    paths.add("base_path", base_path)
    paths.add("db_path", db_path)
    paths.add("lab_submission_directory", lab_submission_directory)
    paths.add("test_files_directory", test_files_directory)
    paths.add(comment("All valid submissions go here within your grader's submission folder."))
    paths.add("valid_dir", valid_dir)
    paths.add(comment("All invalid submissions go here within your grader's submission folder."))
    paths.add("invalid_dir", invalid_dir)
    paths.add(comment("All invalid submissions go here within your grader's submission folder."))
    paths.add("late_dir", late_dir)
    doc['general'] = general
    doc['paths'] = paths

    config = config_path / "mucsmake.toml"

    with open(config, 'w') as f:
        _ = f.write(dumps(doc))
    logger.debug(f"Created default {config}")


def get_config() -> Config:
    if _config is None:
        logger.critical("The config has not been loaded into memory!")
        return None
    return _config


def prepare_config_obj():
    with open("mucsmake.toml", 'r') as f:
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
