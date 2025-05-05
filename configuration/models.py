from pathlib import Path
class Config:
    def __init__(self, mucsv2_instance_code: str, run_valgrind: str, base_path: str, lab_submission_directory: str,
                 test_files_directory: str, valid_dir: str, invalid_dir: str, db_path="", late_dir=""):
        self.mucsv2_instance_code = mucsv2_instance_code
        self.run_valgrind = run_valgrind
        self.base_path = Path(base_path)
        self.lab_submission_directory = self.get_base_path_with_instance_code() / lab_submission_directory
        self.test_files_directory = self.get_base_path_with_instance_code() / test_files_directory
        self.valid_dir = valid_dir
        self.invalid_dir = invalid_dir
        self.late_dir = late_dir
        self.db_path = db_path

    def get_base_path_with_instance_code(self):
        return self.base_path / self.mucsv2_instance_code
