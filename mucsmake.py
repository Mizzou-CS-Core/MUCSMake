# MUCSMakePy
# Utility to collect student lab submissions
# Written by Matt Marlow
# Based on Daphne Zou's original mucsmake script
# Spring 2025

import getpass
import logging
import sys
import os
import shutil
import stat
import build_and_run
from datetime import datetime
from pathlib import Path

# https://pypi.org/project/colorama/
from colorama import init as colorama_init
from colorama import Fore, Back
from colorama import Style
from colorlog import ColoredFormatter

from configuration.config import prepare_toml_doc, prepare_config_obj
from configuration.models import Config
from configuration.config import get_config
from validation.validators import verify_assignment_header_inclusion, verify_assignment_existence, \
    verify_assignment_window, \
    verify_assignment_name, verify_student_enrollment, validate_section
from mucs_database.init import initialize_database


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

CONFIG_FILE = "config.toml"


def mucsmake(username: str, class_code: str, lab_name: str, file_name: str):
    # Stage 1 - Prepare Configuration
    if not os.path.exists(path=CONFIG_FILE):
        print()
        prepare_toml_doc()
        logger.critical(f"{CONFIG_FILE} does not exist, creating a default one")
        exit()
    prepare_config_obj()
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
    enrollment_status = verify_student_enrollment(config_obj=get_config())
    if not enrollment_status:
        print(
            f"{Fore.RED}*** Error: You are not enrolled in {Style.RESET_ALL}{Fore.BLUE}{get_config().mucsv2_instance_code}{Style.RESET_ALL}{Fore.RED} ")
        exit()
    grader = validate_section(username)

    student_temp_dir = prepare_test_directory(get_config(), file_name, lab_name, username)
    # Stage 3 - Compile and Run
    run_errors = compile_and_run_submission(get_config(), student_temp_dir)
    clean_up_test_directory(student_temp_dir)
    # Stage 4 - Place Submission
    place_submission(config_obj=get_config(), lab_window_status=lab_window_status, grader=grader, lab_name=lab_name,
                     file_name=file_name, username=username, run_result=run_errors)
    # Stage 5 - Display Results
    display_results(config_obj=get_config(), lab_window_status=lab_window_status, grader=grader, lab_name=lab_name,
                    file_name=file_name, username=username, run_result=run_errors)


def place_submission(config_obj: Config, lab_window_status: bool, run_result: dict, grader: str, lab_name: str,
                     file_name: str, username: str):
    submission_path = config_obj.lab_submission_directory + "/" + lab_name + "/" + grader
    directory_name = username + "_" + str(datetime.today()).replace(" ", "_")
    valid_path = submission_path + "/" + config_obj.valid_dir
    invalid_path = submission_path + "/" + config_obj.invalid_dir

    is_valid = lab_window_status and run_result.get("no_compile") is None
    os.makedirs(valid_path, exist_ok=True)
    os.makedirs(invalid_path, exist_ok=True)

    if (is_valid):
        valid_student_dir = valid_path + "/" + directory_name
        os.makedirs(valid_student_dir)
        # sets directory to setgroupid, read/execute for users, and nothing else for non groups
        os.chmod(valid_student_dir, 0o2770)
        shutil.copy(file_name, valid_student_dir)
        os.chmod(valid_student_dir + "/" + Path(file_name).name, stat.S_IRUSR | stat.S_IRGRP | stat.S_IXGRP)
        symlink_dir = submission_path + "/" + username
        # if the link existed previously, let's undo it
        if os.path.islink(symlink_dir):
            os.unlink(symlink_dir)
        os.symlink(valid_student_dir, symlink_dir, target_is_directory=True)
    else:
        invalid_student_dir = invalid_path + "/" + directory_name
        os.makedirs(invalid_student_dir)
        shutil.copy(file_name, invalid_student_dir)


def display_results(config_obj: Config, lab_window_status: bool, run_result: bool, grader: str, lab_name: str,
                    file_name: str, username: str):
    print(f"{Fore.BLUE}========================================={Style.RESET_ALL}")
    print(f"Course:     {config_obj.mucsv2_instance_code}")
    print(f"Section/TA: {grader}")
    print(f"Assignment: {lab_name}")
    print(f"User:       {username}")
    print(f"Submission: {file_name}")
    print(f"{Fore.BLUE}========================================={Style.RESET_ALL}")
    print(f"{Fore.BLUE}***********SUBMISSION COMPLETE**********{Style.RESET_ALL}")
    print(f"\n")
    if (lab_window_status == False):
        print(f"{Fore.RED}========================================={Style.RESET_ALL}")
        print(f"{Fore.RED}*******OUTSIDE OF SUBMISSION WINDOW******{Style.RESET_ALL}")
        print(f"{Fore.RED}========================================={Style.RESET_ALL}")
    elif (run_result.get("no_compile") is not None):
        print(f"{Fore.RED}========================================={Style.RESET_ALL}")
        print(f"{Fore.RED}************FAILED TO COMPILE************{Style.RESET_ALL}")
        print(f"{Fore.RED}========================================={Style.RESET_ALL}")
    elif (len(run_result) > 0):
        print(f"{Fore.YELLOW}====================================================={Style.RESET_ALL}")
        print(f"{Fore.YELLOW}**********SUBMISSION SUCCESSFUL WITH ERRORS**********{Style.RESET_ALL}")
        print(f"{Fore.YELLOW}====================================================={Style.RESET_ALL}")
    else:
        print(f"{Fore.GREEN}========================================={Style.RESET_ALL}")
        print(f"{Fore.GREEN}**********SUBMISSION SUCCESSFUL**********{Style.RESET_ALL}")
        print(f"{Fore.GREEN}========================================={Style.RESET_ALL}")


def prepare_test_directory(config_obj: Config, file_name: str, lab_name: str, username: str) -> str:
    lab_files_dir = config_obj.test_files_directory + "/" + lab_name + "_temp"
    student_temp_files_dir = lab_files_dir + "/" + lab_name + "_" + username + "_temp"
    os.makedirs(student_temp_files_dir, exist_ok=True)
    for entry in os.scandir(lab_files_dir):
        if entry.is_dir():
            continue
        shutil.copy(entry.path, student_temp_files_dir)
    shutil.copy(file_name, student_temp_files_dir)
    return student_temp_files_dir


def compile_and_run_submission(config_obj: Config, temp_dir: str) -> bool:
    is_make = False
    for entry in os.scandir(temp_dir):
        if (entry.name == "Makefile"):
            is_make = True
            break
    errors = dict()
    result = build_and_run.compile(compilable_code_path=temp_dir, use_makefile=is_make, filename=file_name)
    # returns 2 if doesnt link
    if (result.returncode != 0):
        print(result.stderr)
        print(f"{Back.RED}*** Error: Submitted program does not compile! ***{Style.RESET_ALL}")
        errors['no_compile'] = "Submitted program does not compile!"
        return errors
    errors = build_and_run.run_executable(path=temp_dir)
    for error in errors.values():
        print(f"{Fore.RED}{error}{Style.RESET_ALL}")
    return errors


def clean_up_test_directory(temp_dir: str):
    shutil.rmtree(temp_dir)


# Creates a new toml file.


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
    prepare_config_obj()
    initialize_database(sqlite_db_path=get_config().db_path, mucsv2_instance_code=get_config().mucsv2_instance_code)
    mucsmake(username, class_code, lab_name, file_name)
