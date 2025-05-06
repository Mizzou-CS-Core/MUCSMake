# MUCSMakePy
# Utility to collect student lab submissions
# Written by Matt Marlow
# Based on Daphne Zou's original mucsmake script
# Spring 2025

import getpass
import logging
import os
import shutil
import stat
import sys
from datetime import datetime
from pathlib import Path

import build_and_run
import mucs_database.submission.accessors as dao_submission
from colorama import Fore
from colorama import Style
# https://pypi.org/project/colorama/
from colorama import init as colorama_init
from colorlog import ColoredFormatter
from mucs_database.init import initialize_database

from configuration.config import prepare_toml_doc, prepare_config_obj, get_config
from validation.validators import verify_assignment_header_inclusion, verify_assignment_existence, \
    verify_assignment_window, \
    verify_assignment_name, validate_section


def setup_logging():
    # everything including debug goes to log file
    root = logging.getLogger()
    root.setLevel(logging.DEBUG)

    fh = logging.FileHandler("mucs_startup.log", encoding="utf-8")
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s:%(lineno)d - %(message)s"
    ))
    # log info and above to console
    ch = logging.StreamHandler()
    ch.setLevel(logging.WARNING)
    # this format string lets colorlog insert color around the whole line
    fmt = "[%(levelname)s]: %(message)s"
    colors = {
        'DEBUG': 'cyan',
        'INFO': 'green',
        'WARNING': 'yellow',
        'ERROR': 'red',
        'CRITICAL': 'bold_red',
    }
    ch.setFormatter(ColoredFormatter(fmt, log_colors=colors))
    root.addHandler(fh)
    root.addHandler(ch)


logger = logging.getLogger(__name__)


def run_procedures(username: str, lab_name: str, file_name: str):
    """
    Runs the validators and compilation procedures for MUCSMake.
    :param username: The pawprint of the submitting user.
    :param lab_name: The name of the assignment submitted to.
    :param file_name: The file name/path of the submission.
    """
    # Stage 2 - Verify Parameters and Submission
    lab_name_status = verify_assignment_name(lab_name)
    if not lab_name_status:
        logger.error(f"Assignment number {lab_name} is invalid. Please check again.")
        exit()
    lab_file_status = verify_assignment_existence(file_name)
    if not lab_file_status:
        logger.error(f"File {file_name} does not exist in the current directory.")
        exit()
    lab_header_inclusion = verify_assignment_header_inclusion(file_name)
    if not lab_header_inclusion:
        logger.warning(f"Your submission {file_name} does not have the assignment header file.")
    lab_window_status = verify_assignment_window()
    if not lab_window_status:
        logger.warning(f"Your submission {file_name} is outside of the allowed submission window.")
    grader = validate_section(username)

    student_temp_dir = prepare_test_directory(file_name, lab_name)
    # Stage 3 - Compile and Run
    run_errors = compile_and_run_submission(student_temp_dir)
    # Stage 4 - Place Submission
    place_submission(is_late=lab_window_status, run_result=run_errors, grading_group_name=grader, lab_name=lab_name,
                     file_name=file_name, username=username)
    # Stage 5 - Display Results
    display_results(is_late=lab_window_status, grading_group_name=grader, lab_name=lab_name,
                    file_name=file_name, username=username, run_result=run_errors)


def place_submission(is_late: bool, run_result: dict, grading_group_name: str, lab_name: str, file_name: str,
                     username: str):
    """
    Creates and places the submission in the appropriate folder on the MUCSv2 filesystem.
    Signs a Submission object in the DB.
    :param is_late: If the submission is late to the assignment.
    :param run_result: The error(s) collected during submission program execution.
    :param grading_group_name: The name of the grading group associated with the submitting user.
    :param lab_name: The name of the assignment submitted to.
    :param file_name: The file name/path of the submission.
    :param username: The pawprint of the submitting user.
    """
    config = get_config()
    submission_path = config.lab_submission_directory / lab_name / grading_group_name
    directory_name = username + "_" + str(datetime.today()).replace(" ", "_")
    valid_path = submission_path / config.valid_dir
    invalid_path = submission_path / config.invalid_dir
    logger.debug("Preparing to place submission")
    logger.debug(f"Submission path: {submission_path}")
    logger.debug(f"Directory name: {directory_name}")
    logger.debug(f"Valid path: {valid_path}")
    logger.debug(f"Invalid path: {invalid_path}")
    # if a submission compiles and isn't late it is eliglibe for grading
    is_valid = is_late and run_result.get("no_compile") is None
    logger.debug(f"Is valid: {is_valid}")
    valid_path.mkdir(exist_ok=True, parents=True)
    invalid_path.mkdir(exist_ok=True, parents=True)
    logger.debug("Created valid and invalid directories (if they didn't exist before)")

    if is_valid:
        valid_student_dir = valid_path / directory_name
        logger.debug(f"Valid student directory: {valid_student_dir} Creating it!")
        valid_student_dir.mkdir()
        # sets directory to setgroupid, read/execute for users, and nothing else for non groups
        valid_student_dir.chmod(mode=0o2770)
        shutil.copy(file_name, valid_student_dir)
        file_name_path = valid_student_dir / Path(file_name).name
        file_name_path.chmod(mode=stat.S_IRUSR | stat.S_IRGRP | stat.S_IXGRP)
        symlink_dir = submission_path / username
        # if the link existed previously, let's undo it
        if symlink_dir.is_symlink():
            symlink_dir.unlink()
        os.symlink(valid_student_dir, symlink_dir, target_is_directory=True)
    else:
        invalid_student_dir = invalid_path / directory_name
        invalid_student_dir.mkdir()
        shutil.copy(file_name, invalid_student_dir)
        file_name_path = invalid_student_dir / Path(file_name).name
    # create an entry of a submission in the DB
    dao_submission.store_submission(person_pawprint=username, assignment_name=lab_name, submission_path=file_name_path,
                                    is_valid=is_valid, is_late=is_late, time_submitted=datetime.now())


def display_results(is_late: bool, run_result: dict, grading_group_name: str, lab_name: str,
                    file_name: str, username: str):
    """
    Displays a readout of the submission results to the calling user.
    :param is_late: If the submission is late to the assignment.
    :param run_result: The error(s) collected during submission program execution.
    :param grading_group_name: The name of the grading group associated with the submitting user.
    :param lab_name: The name of the assignment submitted to.
    :param file_name: The file name/path of the submission.
    :param username: The pawprint of the submitting user.
    """
    print(f"{Fore.BLUE}========================================={Style.RESET_ALL}")
    print(f"Course:     {get_config().mucsv2_instance_code}")
    print(f"Section/TA: {grading_group_name}")
    print(f"Assignment: {lab_name}")
    print(f"User:       {username}")
    print(f"Submission: {file_name}")
    print(f"{Fore.BLUE}========================================={Style.RESET_ALL}")
    print(f"{Fore.BLUE}***********SUBMISSION COMPLETE**********{Style.RESET_ALL}")
    print(f"\n")
    if not is_late:
        print(f"{Fore.RED}========================================={Style.RESET_ALL}")
        print(f"{Fore.RED}*******OUTSIDE OF SUBMISSION WINDOW******{Style.RESET_ALL}")
        print(f"{Fore.RED}========================================={Style.RESET_ALL}")
    elif run_result.get("no_compile") is not None:
        print(f"{Fore.RED}========================================={Style.RESET_ALL}")
        print(f"{Fore.RED}************FAILED TO COMPILE************{Style.RESET_ALL}")
        print(f"{Fore.RED}========================================={Style.RESET_ALL}")
    elif len(run_result) > 0:
        print(f"{Fore.YELLOW}====================================================={Style.RESET_ALL}")
        print(f"{Fore.YELLOW}**********SUBMISSION SUCCESSFUL WITH ERRORS**********{Style.RESET_ALL}")
        print(f"{Fore.YELLOW}====================================================={Style.RESET_ALL}")
    else:
        print(f"{Fore.GREEN}========================================={Style.RESET_ALL}")
        print(f"{Fore.GREEN}**********SUBMISSION SUCCESSFUL**********{Style.RESET_ALL}")
        print(f"{Fore.GREEN}========================================={Style.RESET_ALL}")


def prepare_test_directory(file_name: str, lab_name: str) -> str:
    """
    Creates a testing directory on the user's local directory
    Copies relevant files from MUCSv2 backend
    :param file_name: The name of the file being submitted
    :param lab_name: The assignment being submitted to
    :return:
    """
    temp_lab_dir = get_config().cwd / f"{lab_name}_temp"
    logger.debug(f"Creating {temp_lab_dir}")
    temp_lab_dir.mkdir(exist_ok=True)

    lab_files_dir = get_config().test_files_directory / f"{lab_name}"
    logger.debug(f"Retrieving files from {lab_files_dir}")
    for entry in lab_files_dir.iterdir():
        if entry.is_dir():
            continue
        logger.debug(f"Copying {entry} into {temp_lab_dir}")
        shutil.copy(entry, temp_lab_dir)
    logger.debug(f"Copying student's {file_name} to {temp_lab_dir}")
    shutil.copy(file_name, temp_lab_dir)
    return temp_lab_dir


def compile_and_run_submission(temp_dir: str) -> dict[str, str]:
    """
    Compiles and runs a C submission.
    :param temp_dir: A path to the directory containing the compilable code
    :return: A dictionary of errors
    """
    is_make = False
    for entry in os.scandir(temp_dir):
        if entry.name == "Makefile":
            is_make = True
            break
    errors = dict()
    result = build_and_run.compile(compilable_code_path=temp_dir, use_makefile=is_make, filename=file_name)
    # returns 2 if doesnt link
    if result.returncode != 0:
        logging.error(f"Submitted program does not compile!")
        errors['no_compile'] = "Submitted program does not compile!"
        shutil.rmtree(temp_dir)
        return errors
    errors = build_and_run.run_executable(path=temp_dir)
    if len(errors) > 0:
        logging.warning(f"There were {len(errors)} errors in your submission. ")
    for error in errors.values():
        logging.warning(f"{error}")
    shutil.rmtree(temp_dir)
    return errors



if __name__ == "__main__":
    # Stage 0 - Collect Command Args
    username = getpass.getuser()
    setup_logging()
    colorama_init()
    if len(sys.argv) < 4:
        logger.error("Too few arguments provided!")
        logger.error("Usage: mucsmake class_code assignment_name file_to_submit")
        exit()
    class_code = sys.argv[1]
    lab_name = sys.argv[2]
    file_name = sys.argv[3]
    if os.path.isdir(file_name):
        # edge case to catch during preappended absolute paths
        logger.error("Too few arguments provided!")
        logger.error("Usage: mucsmake class_code assignment_name file_to_submit")
        exit()
    if not os.path.exists(path="config.toml"):
        print()
        prepare_toml_doc()
        logger.critical("config.toml does not exist, creating a default one")
        exit()
    prepare_config_obj()
    initialize_database(sqlite_db_path=get_config().db_path, mucsv2_instance_code=get_config().mucsv2_instance_code)
    run_procedures(username, lab_name, file_name)
