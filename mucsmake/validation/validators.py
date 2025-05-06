import logging
import os
import re
from datetime import datetime, timezone

import mucs_database.assignment.accessors as dao_assignment
import mucs_database.person.accessors as dao_person
from mucs_database.grading_group.model import GradingGroup

_assignment: dict = dict()


def verify_assignment_header_inclusion(file_name: str) -> bool:
    """
    Checks if the submitted file contains the relevant C header inclusion.
    :param file_name: A path to the submitted file.
    :return: True if it does, False if it does not.
    """
    lab_name = _assignment.get("mucsv2_name")
    logging.debug(f"Verifying if the header file is included with {file_name}")
    search_pattern = rf"^(#include)\s*(\"{lab_name}.h\")"
    with open(file_name, 'r') as c_file:
        for line in c_file:
            if re.search(search_pattern, line):
                return True
    return False


def verify_assignment_existence(file_name: str) -> bool:
    """
    Checks if the declared file path actually exists.
    :param file_name: A path to the submission.
    :return: True if it does, False if it does not.
    """
    logging.debug(f"Checking if {file_name} exists")
    return os.path.exists(file_name)


def verify_assignment_window() -> bool:
    """
    Checks if the intended assignment is open for submissions.
    :return: True if it is, False if it is not.
    """
    asn_name = _assignment.get("mucsv2_name")
    logging.debug(f"Verifying the time window of {asn_name}")
    # the time formats from _assignment are non-naive, so we need to give today a UTC designator
    today = datetime.now(timezone.utc)
    start_date = datetime.fromisoformat(_assignment['open_at'].replace('Z', '+00:00'))
    end_date = datetime.fromisoformat(_assignment['due_at'].replace('Z', '+00:00'))
    is_on_time = start_date < today < end_date
    logging.debug(f"Time window result: {is_on_time}")
    return is_on_time


def verify_assignment_name(assignment_name: str) -> bool:
    """
    Checks if the assignment specified actully exists.
    Assigns the assignment model to a global for future cache use.
    :param assignment_name: The name of the intended assignment to submit to.
    :return: True if it does exist, False if it does not. _assignment defined in validator namespace.
    """
    logging.debug(f"Verifying lab name: {assignment_name}")
    global _assignment
    _assignment = dao_assignment.get_assignment_by_name(name=assignment_name)
    if _assignment is None:
        logging.error(f"There is no corresponding lab name for {assignment_name}")
        return False
    logging.info(f"{assignment_name} was found.")
    return True


# def verify_student_enrollment(config_obj: Config):
#     path = os.environ.get("PATH", "")
#     directories = path.split(":")
#     target = config_obj.get_base_path_with_instance_code() + "/bin"
#     if target in directories:
#         return True
#     return False


def validate_section(username: str) -> str:
    """
    Determines the grading group of the submitting user.
    :param username: The submitting user's pawprint.
    :return: The name of the found grading group. Returns "" if there is no group (and critical error)
    """
    grading_group: GradingGroup = dao_person.get_person_grading_group(pawprint=username, return_dict=False)
    if grading_group is None:
        logging.critical(f"No grading group was found for pawprint: {username}")
        return ""
    return grading_group.name
