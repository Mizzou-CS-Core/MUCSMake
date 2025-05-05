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

from csv import DictReader

from configuration.config import prepare_toml_doc, prepare_config_obj
from configuration.models import Config
from validation.validators import verify_assignment_header_inclusion, verify_assignment_existence, verify_assignment_window, \
    verify_assignment_name, verify_student_enrollment


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
    ch.setLevel(logging.INFO)
    # this format string lets colorlog insert color around the whole line
    fmt = "%(log_color)s%(asctime)s [%(levelname)s] %(name)s: %(message)s"
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
date_format = "%Y-%m-%d_%H:%M:%S"


def main(username: str, class_code: str, lab_name: str, file_name: str):
    # Stage 1 - Prepare Configuration
    if not os.path.exists(path=CONFIG_FILE):
        print()
        prepare_toml_doc()
        handle_critical_error(f"{CONFIG_FILE} does not exist, creating a default one", "main")
        exit()
    config_obj: Config = prepare_config_obj()
    # Stage 2 - Verify Parameters and Submission
    lab_name_status = verify_assignment_name(lab_name)
    if not lab_name_status:
        print(f"{Fore.RED}*** Error: Lab number missing or invalid. Please check again. ***{Style.RESET_ALL}")
        exit()
    lab_file_status = verify_assignment_existence(file_name)
    if not lab_file_status:
        print(f"{Fore.RED}*** Error: file {Style.RESET_ALL}{Fore.BLUE}{file_name}{Style.RESET_ALL}{Fore.RED} does not exist in the current directory. ***{Style.RESET_ALL}")
        exit()
    lab_header_inclusion = verify_assignment_header_inclusion(file_name)
    if not lab_header_inclusion:
        print(f"{Fore.YELLOW}*** Warning: your submission {Style.RESET_ALL}{Fore.BLUE}{file_name}{Style.RESET_ALL}{Fore.YELLOW} does not include the lab header file. ***{Style.RESET_ALL}")
        print(f"{Fore.YELLOW}*** There's a good chance your program won't compile! ***{Style.RESET_ALL}")
    lab_window_status = verify_assignment_window()
    if not lab_window_status:
        print(f"{Fore.YELLOW}*** Warning: your submission {Style.RESET_ALL}{Fore.BLUE}{file_name}{Style.RESET_ALL}{Fore.YELLOW} is outside of the submission window. ***{Style.RESET_ALL}")
    enrollment_status = verify_student_enrollment(config_obj)
    if not enrollment_status:
        print(f"{Fore.RED}*** Error: You are not enrolled in {Style.RESET_ALL}{Fore.BLUE}{config_obj.mucsv2_instance_code}{Style.RESET_ALL}{Fore.RED} ")
        exit()
    grader = determine_section(config_obj, username)
    
    student_temp_dir = prepare_test_directory(config_obj, file_name, lab_name, username)
    # Stage 3 - Compile and Run
    run_errors = compile_and_run_submission(config_obj, student_temp_dir)
    clean_up_test_directory(student_temp_dir)
    # Stage 4 - Place Submission
    place_submission(config_obj=config_obj, lab_window_status=lab_window_status, grader=grader, lab_name=lab_name, file_name=file_name, username=username, run_result=run_errors)
    # Stage 5 - Display Results
    display_results(config_obj=config_obj, lab_window_status=lab_window_status, grader=grader, lab_name=lab_name, file_name=file_name, username=username, run_result=run_errors)



def place_submission(config_obj: Config, lab_window_status: bool, run_result: dict, grader: str, lab_name: str, file_name: str, username: str):
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
        os.symlink(valid_student_dir, symlink_dir, target_is_directory = True)
    else:
        invalid_student_dir = invalid_path + "/" + directory_name
        os.makedirs(invalid_student_dir)
        shutil.copy(file_name, invalid_student_dir)
    
    
def display_results(config_obj: Config, lab_window_status: bool, run_result: bool, grader: str, lab_name: str, file_name: str, username: str):
    
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
    elif(len(run_result) > 0):
        print(f"{Fore.YELLOW}====================================================={Style.RESET_ALL}")
        print(f"{Fore.YELLOW}**********SUBMISSION SUCCESSFUL WITH ERRORS**********{Style.RESET_ALL}")
        print(f"{Fore.YELLOW}====================================================={Style.RESET_ALL}")
    else:
        print(f"{Fore.GREEN}========================================={Style.RESET_ALL}")
        print(f"{Fore.GREEN}**********SUBMISSION SUCCESSFUL**********{Style.RESET_ALL}")
        print(f"{Fore.GREEN}========================================={Style.RESET_ALL}")






def determine_section(config_obj: Config, username: str) -> str:
    try:
        for roster_filename in os.listdir(config_obj.roster_directory):
            with open(config_obj.roster_directory + "/" + roster_filename, 'r') as csv_file:
                _ = next(csv_file)
                fieldnames = ['pawprint', 'canvas_id', 'name', 'date']
                csv_roster = DictReader(csv_file, fieldnames=fieldnames)
                for row in csv_roster:
                    if username == row['pawprint']:
                        return roster_filename.replace(".csv", '')
    except UnicodeDecodeError as e:
        handle_critical_error(message=f"{str(e)} - likely misconfigured roster data", calling_function="determine_section")
    # if we made it out of the loop... panic!
    # likely a misconfiguration of the grading roster
    handle_critical_error("No grader found", "determine_section")
    return ""

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
    colorama_init()
    if (len(sys.argv) < 4):
        print(f"{Fore.RED} *** Too few arguments provided! *** {Style.RESET_ALL}")
        print(f"{Fore.RED}Usage: mucsmake{Fore.BLUE} {{class_code}} {{lab_name}} {{file_to_submit}} {Style.RESET_ALL}")
        exit()
    class_code = sys.argv[1]
    lab_name = sys.argv[2]
    file_name = sys.argv[3]
    if (os.path.isdir(file_name)):
        # edge case to catch during preappended absolute paths
        print(f"{Fore.RED} *** Too few arguments provided! *** {Style.RESET_ALL}")
        print(f"{Fore.RED}Usage: mucsmake{Fore.BLUE} {{class_code}} {{lab_name}} {{file_to_submit}} {Style.RESET_ALL}")
        exit()
    main(username, class_code, lab_name, file_name)



