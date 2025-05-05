import logging
import os
import re
from datetime import datetime

from configuration.models import Config

import mucs_database.assignment.accessors as dao_assignment

_assignment: dict = dict()


def verify_assignment_header_inclusion(file_name: str) -> bool:
    lab_name = _assignment.get("mucsv2_name")
    logging.debug(f"Verifying if the header file is included with {file_name}")
    search_pattern = rf"^(#include)\s*(\"{lab_name}.h\")"
    with open(file_name, 'r') as c_file:
        for line in c_file:
            if re.search(search_pattern, line):
                return True
    return False


def verify_assignment_existence(file_name: str) -> bool:
    logging.debug(f"Checking if {file_name} exists")
    return os.path.exists(file_name)


def verify_assignment_window() -> bool:
    asn_name = _assignment.get("mucsv2_name")
    logging.debug(f"Verifying the time window of {asn_name}")
    today = datetime.today()
    start_date = _assignment['open_at']
    end_date = _assignment['due_at']
    is_on_time = start_date < today < end_date
    logging.debug(f"Time window result: {is_on_time}")
    return is_on_time


def verify_assignment_name(assignment_name: str) -> bool | None:
    logging.debug(f"Verifying lab name: {assignment_name}")
    global _assignment
    _assignment = dao_assignment.get_assignment_by_name(name=assignment_name)
    if _assignment is None:
        logging.error(f"There is no corresponding lab name for {assignment_name}")
        return False
    logging.info(f"{assignment_name} was found.")
    return True


def verify_student_enrollment(config_obj: Config):
    path = os.environ.get("PATH", "")
    directories = path.split(":")
    target = config_obj.get_base_path_with_instance_code() + "/bin"
    if target in directories:
        return True
    return False
