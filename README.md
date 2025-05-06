# MUCSMake
*Part of the MUCSv2 family of applications*

*Installed during MUCSv2 initialization*

**This application is dependent on an existing MUCSv2 Instance to pair with.**

Student facing utility for submitting C assignments to a MUCSv2 Instance.

- **Robust set of pre-compilation validation, including:**
  - Assignment header inclusion
  - Assignment definition
  - Lateness
  - Grading group check
- **Configurable compile-time and run-time checks, including**
  - Makefile specification
  - Compile fail reasoning
  - Runtime output displayed to end-user
  - Test strings
  - Valgrind run and output
  - Submission record keeping
The user is informed of failures in code running, but instructors can view individualized logs for each submission made for debugging purposes.

# Set Up

*Many of these set up steps are performed automatically if you have initialized your MUCSv2 course instance correctly using https://github.com/Mizzou-CS-Core/MUCS_Startup*. 




A Python 3.7+ interpreter is required. It is recommended that you create a Python virtual environment for using this application.
There are some required modules in MUCSMake. You can install them with `pip install -r requirements.txt`. 

To configure runtime properties, first run the program at least once. This will create an editable `config.toml` document that you can edit with your specifications. You will need to specify a database file path and the MUCSv2 instance code associated with your MUCSv2 instance. 

For each assignment, you should have a directory corresponding to the name in `data/test_files` of your MUCSv2 instance. (This is done automatically during MUCSv2 initialization). You will need to place the C source code, headers, and optionally Makefiles corresponding to the assignment. (MUCSMake will detect if the assignment uses a Makefile.)

# Usage

There are two methods of running the program.

If you would like to use the Bash wrapper script (useful for student usage), you can run `./mucsmake`. This will automatically open a virtual environment, run the Python script, then close the environment.

Otherwise, you can activate your virtual environment and run `python3 mucsmake.py`.

In both instances, you will need to specify 1. your MUCSv2 instance code 2. the name of the assignment you're submitting to, and 3. the file path to the submission. 

This looks like `mucsmake {mucs_instance_code} {assignment_name} {submission_file_path}`







