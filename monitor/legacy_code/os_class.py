import ctypes
import os
import sys
import ctypes
from ctypes import c_char_p, c_size_t, c_void_p, POINTER, c_ubyte, c_bool
import platform
import re
from datetime import datetime
import uuid
import hashlib
import shutil
import subprocess
import psutil
import zipfile
import tempfile
# import time
import sys
from pathlib import Path
#from monitor.utils.path_utils import get_app_root
if sys.platform.startswith("Windows"):
    from win32com.client import Dispatch

class os_manager:
    def __init__(self, parent = None):
        self.parent = parent
        self.current_os = platform.system()
        #print("current_os: ",self.current_os)
        self.executable_extension = ".exe" if self.current_os == "Windows" else ""
    
    def get_executable_name(self, file_path):
        base = os.path.basename(file_path)
        if self.current_os == "Windows" and base.lower().endswith('.exe'):
            return base.lower()
        else:
            return base  # On Linux, executables typically have no extension
    
    # IMPORTANT FOR DAN
    def restart_pc(self):
        """
        Restarts the PC.
        """
        if not getattr(sys, 'frozen', False) or not self.parent.enable_pc_restart:  # avoid restarting when debugging/developing
            print("DEBUG Avoiding restart, debugging mode")
            print("DEBUG: self.parent.enable_pc_restart: ", self.parent.enable_pc_restart)
            return
        
        if self.current_os == "Windows":
            os.system("shutdown /r /t 1")
        elif self.current_os == "Linux":
            os.system("sudo shutdown -r now")
        else:
            print(f"Unsupported OS for restart: {self.current_os}")

    def close_then_open_file(self, file_path):
        """
        Closes the executable if it's running and reopens it in a new terminal.
        """
        exe_name = self.get_executable_name(file_path)
        for proc in psutil.process_iter(['pid', 'name']):
            if proc.info['name'].lower() == exe_name.lower():
                proc.terminate()  # Terminate the process
                proc.wait()  # Wait for the process to terminate
        # Open the file in a new terminal
        self.open_file_in_terminal(file_path)

    # IMPORTANT FOR DAN
    def open_file(self, file_path):
        """
        First closes the executable if it's running, then opens it in a new terminal window.
        Returns True if the file was successfully opened, False if there was an error.
        Works on both Windows and Linux (Jetson).
        """
        # Get the executable name and terminate any running instances
        exe_name = self.get_executable_name(file_path)
        try:
            for proc in psutil.process_iter(['pid', 'name']):
                try:
                    if proc.info['name'].lower() == exe_name.lower():
                        print(f"Terminating running instance of {exe_name}")
                        proc.terminate()
                        # Add timeout for process termination (5 seconds)
                        try:
                            proc.wait(timeout=20)  # Wait for the process to terminate with timeout
                            print(f"DEBUG: Successfully terminated {exe_name}")
                        except psutil.TimeoutExpired:
                            print(f"DEBUG: Timeout waiting for {exe_name} to terminate, forcing kill")
                            proc.kill()  # Force kill if timeout
                            proc.wait(timeout=20)  # Give it 20 more seconds to die
                        except Exception as e:
                            print(f"DEBUG: Error waiting for process termination: {e}")
                except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess) as e:
                    print(f"DEBUG: Error accessing process info: {e}")
                    continue
                except Exception as e:
                    print(f"DEBUG: Unexpected error in process iteration: {e}")
                    self.restart_pc()
                    continue
        except Exception as e:
            print(f"DEBUG: Error during process termination loop: {e}")
            self.restart_pc()

        print("DEBUG: Attempting to open in new terminal")

        # Get the full path to the executable and ensure it exists
        full_path = os.path.abspath(file_path)
        if not os.path.exists(full_path):
            print(f"Error: File does not exist: {full_path}")
            return False


        # Platform-specific handling
        try:
            if os.name == 'nt':  # Windows
                # Use 'start' command to explicitly open a new terminal window
                subprocess.Popen(['start', 'cmd', '/K', full_path], shell=True)
                print("DEBUG: Using start cmd /K to open new Windows terminal")

            elif os.name == 'posix':  # Linux (Jetson and other POSIX systems)
                # Try multiple terminal options for Jetson Orin Nano compatibility
                terminals_to_try = [
                    ("gnome-terminal", ["--", "bash", "-c", f"cd '{os.path.dirname(full_path)}' && '{full_path}'; echo 'Press Enter to close...'; read"]),
                    ("x-terminal-emulator", ["-e", "bash", "-c", f"cd '{os.path.dirname(full_path)}' && '{full_path}'; echo 'Press Enter to close...'; read"]),
                    ("xterm", ["-e", "bash", "-c", f"cd '{os.path.dirname(full_path)}' && '{full_path}'; echo 'Press Enter to close...'; read"]),
                    ("konsole", ["-e", "bash", "-c", f"cd '{os.path.dirname(full_path)}' && '{full_path}'; echo 'Press Enter to close...'; read"])
                ]
                
                terminal_found = False
                for terminal_name, args in terminals_to_try:
                    terminal_path = shutil.which(terminal_name)
                    if terminal_path:
                        cmd = [terminal_path] + args
                        print(f"DEBUG: Found terminal {terminal_name}, using command: {cmd}")
                        try:
                            subprocess.Popen(cmd, shell=False)
                            terminal_found = True
                            break
                        except Exception as e:
                            print(f"DEBUG: Failed to launch with {terminal_name}: {e}")
                            continue
                
                if not terminal_found:
                    print("DEBUG: No suitable terminal emulator found. Tried: gnome-terminal, x-terminal-emulator, xterm, konsole")
                    return False

            else:
                raise NotImplementedError("Unsupported operating system")
                
            return True
            
        except Exception as e:
            print(f"DEBUG: Error opening file {full_path}: {e}")
            return False

    def open_file_in_terminal(self, file_path):
        """
        Opens the executable in a new terminal based on the OS.
        """
        try:
            # Get the full path and ensure it exists
            full_path = os.path.abspath(file_path)
            if not os.path.exists(full_path):
                raise FileNotFoundError(f"File does not exist: {full_path}")

            if self.current_os == "Windows":
                # Windows: Use 'start' to open in a new CMD window that stays open
                subprocess.Popen(['cmd', '/K', full_path], shell=True)

            elif self.current_os == "Linux":
                # Linux: Try gnome-terminal (Jetson default), xterm, or konsole
                terminal = shutil.which("gnome-terminal") or shutil.which("xterm") or shutil.which("konsole")
                if terminal:
                    # Quote the path and keep terminal open
                    subprocess.Popen([terminal, '--', 'bash', '-c', f'"{full_path}"; exec bash'], shell=False)
                else:
                    raise RuntimeError("No suitable terminal emulator found (gnome-terminal, xterm, konsole).")

            else:
                raise NotImplementedError(f"Unsupported OS: {self.current_os}")

        except Exception as e:
            print(f"Failed to open file {full_path} in terminal: {e}")
            self.restart_pc()

    def extract_file(self,zip_path, save_path):
        try:
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(save_path)
                members = zip_ref.namelist()

                if not members:
                    print(f"DEBUG: Zip archive '{zip_path}' is empty. Returning save_path: {save_path}") #DEBUG
                    return save_path

                extracted_file_name = None

                # Priority 1: Look for a file ending with .exe (covers Windows and Linux if .exe is used)
                for member_name in members:
                    if member_name.lower().endswith(".exe") and not member_name.endswith('/'): # ensure it's not a dir ending with .exe/
                        candidate_path = os.path.join(save_path, member_name)
                        if os.path.isfile(candidate_path):
                            extracted_file_name = member_name
                            print(f"DEBUG: Found .exe candidate: {candidate_path}") #DEBUG
                            break
                
                # Priority 2: If no .exe found, and on Linux (or non-Windows).
                if not extracted_file_name and self.current_os != "Windows": # Check for non-Windows OS
                    print(f"DEBUG: No .exe found, OS is {self.current_os}. Checking Linux-specific logic.") #DEBUG
                    if len(members) == 1:
                        member_name = members[0]
                        if not member_name.endswith('/'): # Ensure it's not just a directory entry
                            candidate_path = os.path.join(save_path, member_name)
                            if os.path.isfile(candidate_path):
                                 extracted_file_name = member_name
                                 print(f"DEBUG: Single member in zip on {self.current_os}, identified as: {candidate_path}") #DEBUG
                    elif len(members) > 1:
                        print(f"DEBUG: Multiple members on {self.current_os}. Looking for a single no-extension file.") #DEBUG
                        no_ext_candidates = []
                        for member_name in members:
                            # Check if it's a file (not ending with /) and has no extension
                            if not member_name.endswith('/') and not os.path.splitext(member_name)[1]:
                                 candidate_path = os.path.join(save_path, member_name)
                                 if os.path.isfile(candidate_path):
                                    no_ext_candidates.append(member_name)
                        
                        if len(no_ext_candidates) == 1:
                            extracted_file_name = no_ext_candidates[0]
                            print(f"DEBUG: Found single no-extension candidate on {self.current_os}: {os.path.join(save_path, extracted_file_name)}") #DEBUG
                        else:
                            print(f"DEBUG: On {self.current_os} with multiple files and no .exe, found {len(no_ext_candidates)} candidates with no extension. Files: {members}, No-extension Candidates: {no_ext_candidates}. Cannot uniquely identify.") #DEBUG

                if extracted_file_name:
                    full_extracted_path = os.path.join(save_path, extracted_file_name)
                    # Final check that this path is indeed a file
                    if os.path.isfile(full_extracted_path):
                        print(f"DEBUG: Successfully identified and returning executable path: {full_extracted_path}") #DEBUG
                        return full_extracted_path
                    else:
                        # This should ideally not be reached if previous checks for os.path.isfile(candidate_path) are correct
                        print(f"DEBUG: Identified name '{extracted_file_name}' but final path '{full_extracted_path}' is not a file. Fallback.") #DEBUG
                
                # Fallback: If no specific executable file was identified
                print(f"DEBUG: Could not uniquely identify a single executable in '{zip_path}' (OS: {self.current_os}, Members: {members}). Returning extraction directory: {save_path}") #DEBUG
                return save_path
        except zipfile.BadZipFile:
            print(f"Error: '{zip_path}' is not a valid zip file or is corrupted.") #DEBUG
            return None # Or raise an exception, or return save_path depending on desired error handling
        except Exception as e:
            print(f"Error extracting '{zip_path}': {e}") #DEBUG
            return None # Or raise, or return save_path

    def move_updated_EinTzofiaMonitor_to_its_folder(self, path):
        """
        Moves EinTzofiaMonitor file that was downloaded from the server to its location in the Monitor folder, and returns the path to it.
        """
        # Determine the expected executable name based on OS
        if self.current_os == "Windows":
            expected_name = 'EinTzofiaMonitor.exe'
        else:
            expected_name = 'EinTzofiaMonitor'

        new_exe_path = self.find_file_in_folder_by_pattern(path, expected_name)
        new_exe_path = os.path.normpath(new_exe_path)
        
        # Check if the path exists and is a file
        if os.path.exists(new_exe_path) and os.path.isfile(new_exe_path):
            current_exe_path = self.get_EinTzofiaMonitor_path()
            destination_path = os.path.dirname(current_exe_path)
            shutil.move(new_exe_path, destination_path)
            return os.path.join(destination_path, os.path.basename(new_exe_path))
        else:
            print(f"Executable {expected_name} not found in {path}")
            return None

    def find_file_in_folder_by_pattern(self, path, file_name):
        for filename in os.listdir(path):
            if filename.startswith(file_name):
                return os.path.join(path, filename)
        return False   

    def get_EinTzofiaMonitor_path(self):
        EinTzofia_dir_path = os.path.dirname(self.parent.settings['File_Path'])
        base_dir = os.path.dirname(EinTzofia_dir_path)
        monitor_dir_path = os.path.join(base_dir, 'Monitor')
        if self.current_os == "Windows":
            return os.path.join(monitor_dir_path, 'EinTzofiaMonitor.exe')
        else:
            return os.path.join(monitor_dir_path, 'EinTzofiaMonitor')

    def copy_folder_structure(self, src, dst):
        if not os.path.exists(dst):
            os.makedirs(dst)

        # Copy the configfile.pkl from the root of temp
        configfile_path = os.path.join(src, "configfile.pkl")
        if os.path.exists(configfile_path):
            shutil.copy2(configfile_path, dst)

        # Traverse the directory tree
        for item in os.listdir(src):
            item_path = os.path.join(src, item)

            if os.path.isdir(item_path) and item != "snapshots":
                # If it's a directory and not the "snapshots" folder
                new_dst = os.path.join(dst, item)

                # Remove the destination directory if it exists
                if os.path.exists(new_dst):
                    shutil.rmtree(new_dst)
                
                shutil.copytree(item_path, new_dst, ignore=shutil.ignore_patterns("snapshots", "*.db", "*.sqlite", "*.sql", "*.txt", "*.log"))
            elif os.path.isfile(item_path) and item == "configfile.pkl":
                # If it's the configfile.pkl file
                shutil.copy2(item_path, dst)

    def delete_folder_by_path(self, folder_path):
        if os.path.exists(folder_path) and os.path.isdir(folder_path):
            shutil.rmtree(folder_path)
            return True
        else:
            return False

    def delete_old_shortcuts(self, shortcut_name):
        """
        Deletes older shortcuts in the startup folder, keeping only the newest one.
        Works with both dated shortcuts (Monitor_DD-MM-YY) and shortcuts with preserved
        executable names.
        
        Args:
            shortcut_name: Base name of the shortcut (e.g., "Monitor")
            
        Returns:
            Path to the latest shortcut file that was kept, or None if no matching shortcuts found
        """
        print(f"Deleting old shortcuts that begin with or contain: {shortcut_name}")
        
        if self.current_os == "Windows":
            startup_folder = os.path.join(os.getenv('APPDATA'), 'Microsoft', 'Windows', 'Start Menu', 'Programs', 'Startup')
            extension = '.lnk'
        elif self.current_os == "Linux":
            startup_folder = os.path.expanduser('~/.config/autostart')
            extension = '.desktop'
        else:
            print(f"Unsupported OS for deleting shortcuts: {self.current_os}")
            return None
            
        print(f"Checking startup folder: {startup_folder}")
        
        if not os.path.exists(startup_folder):
            print(f"Startup folder does not exist: {startup_folder}")
            return None
        
        all_files = os.listdir(startup_folder)
        print(f"Found {len(all_files)} files in startup folder")
        
        matching_files = []
        for filename in all_files:
            # Check if filename contains the shortcut_name (case-insensitive) and has the right extension
            if shortcut_name.lower() in filename.lower() and filename.lower().endswith(extension.lower()):
                file_path = os.path.join(startup_folder, filename)
                print(f"Found matching file: {filename}")
                matching_files.append((file_path, os.path.getmtime(file_path)))
        
        if not matching_files:
            print(f"No matching shortcuts found containing: {shortcut_name}")
            return None
            
        # Sort by creation time (newest last)
        matching_files.sort(key=lambda x: x[1])
        
        # Keep the most recently created shortcut
        latest_file = matching_files[-1][0]
        latest_filename = os.path.basename(latest_file)
        print(f"Keeping latest file: {latest_filename} (modified: {datetime.fromtimestamp(matching_files[-1][1])})")
        
        # Delete all other matching shortcuts
        files_to_delete = [file[0] for file in matching_files[:-1]]
        print(f"Files to delete: {len(files_to_delete)}")
        
        for file_path in files_to_delete:
            try:
                delete_filename = os.path.basename(file_path)
                print(f"Deleting file: {delete_filename}")
                os.remove(file_path)
                print(f"Successfully deleted: {delete_filename}")
            except Exception as e:
                print(f"Error deleting file {os.path.basename(file_path)}: {e}")
                
        return latest_file

    def keep_latest_exe(self, pattern, destination_folder):
        # Ensure the destination folder exists
        if not os.path.exists(destination_folder):
            raise FileNotFoundError(f"The destination folder '{destination_folder}' does not exist.")

        if self.current_os == "Windows":
            full_pattern = rf'(?i){re.escape(pattern)}_(\d{{2}}-\d{{2}}-\d{{2}})\.exe'
        elif self.current_os == "Linux":
            full_pattern = rf'(?i){re.escape(pattern)}_(\d{{2}}-\d{{2}}-\d{{2}})(?:\.sh|\.run)?$'
        else:
            print(f"Unsupported OS for keeping latest executable: {self.current_os}")
            return None

        latest_file = None
        latest_date = None
        files_to_delete = []

        # Iterate through files in the destination folder
        for filename in os.listdir(destination_folder):
            match = re.match(full_pattern, filename)
            if match:
                file_path = os.path.join(destination_folder, filename)
                try:
                    file_date = datetime.strptime(match.group(1), '%d-%m-%y')
                except ValueError:
                    continue  # Skip files with invalid date format

                if latest_date is None or file_date > latest_date:
                    if latest_file:
                        files_to_delete.append(latest_file)
                    latest_file = file_path
                    latest_date = file_date
                else:
                    files_to_delete.append(file_path)

        # Delete older files
        for file_path in files_to_delete:
            try:
                os.remove(file_path)
            except OSError:
                pass  # Silently ignore errors in deletion

        return latest_file

    def delete_file(self, file_path):
        try:
            os.remove(file_path)
            print(f"File {file_path} has been deleted.")
        except FileNotFoundError:
            print(f"File {file_path} not found.")
        except PermissionError:
            print(f"Permission denied: unable to delete {file_path}.")
        except Exception as e:
            print(f"Error deleting file {file_path}: {e}")

    # IMPORTANT FOR DAN
    def get_hardware_info(self):
        cpu_info = ""
        system_uuid = ""
        drive_serial = ""

        if self.current_os.lower() == "windows":
            # Windows-specific code - get static hardware info only
            try:
                cpu_info = subprocess.check_output(
                    'powershell -command "Get-CimInstance -ClassName Win32_Processor | Select-Object -ExpandProperty Name"',
                    shell=True, text=True
                ).strip()
            except Exception as e:
                print(f"Failed to retrieve CPU info on Windows: {e}")
                cpu_info = "Unknown CPU"

            try:
                system_uuid = subprocess.check_output(
                    'powershell -command "Get-CimInstance -ClassName Win32_ComputerSystemProduct | Select-Object -ExpandProperty UUID"',
                    shell=True, text=True
                ).strip()
            except Exception as e:
                print(f"Failed to retrieve system UUID on Windows: {e}")
                system_uuid = str(uuid.getnode())

            # NEW: Get primary hard drive serial number for additional uniqueness
            try:
                drive_serial = subprocess.check_output(
                    'powershell -command "Get-CimInstance -ClassName Win32_DiskDrive | Where-Object {$_.Index -eq 0} | Select-Object -ExpandProperty SerialNumber"',
                    shell=True, text=True
                ).strip()
            except Exception as e:
                print(f"Failed to retrieve drive serial on Windows: {e}")
                # Fallback: try getting any available disk serial
                try:
                    drive_serial = subprocess.check_output(
                        'powershell -command "Get-CimInstance -ClassName Win32_DiskDrive | Select-Object -First 1 -ExpandProperty SerialNumber"',
                        shell=True, text=True
                    ).strip()
                except Exception as e2:
                    print(f"Failed to retrieve any drive serial on Windows: {e2}")
                    drive_serial = "Unknown Drive"

        elif self.current_os.lower() == "linux":
            # Linux-specific code - use ONLY the most reliable identifiers
            # Get CPU model from /proc/cpuinfo (always reliable)
            try:
                with open("/proc/cpuinfo", "r") as f:
                    cpuinfo_content = f.read()
                
                # Extract only the model name, not dynamic info
                cpu_model = "Unknown CPU"
                for line in cpuinfo_content.split('\n'):
                    if line.startswith('model name'):
                        cpu_model = line.split(':')[1].strip()
                        break
                
                cpu_info = cpu_model
                
            except Exception as e:
                print(f"Failed to retrieve CPU info from /proc/cpuinfo: {e}")
                cpu_info = "Unknown CPU"

            # Get machine ID - use ONLY /etc/machine-id for consistency
            try:
                with open("/etc/machine-id", "r") as f:
                    system_uuid = f.read().strip()
            except (FileNotFoundError, PermissionError) as e:
                print(f"Machine ID not available: {e}")
                # Use deterministic fallback that both apps will compute identically
                system_uuid = self._get_deterministic_system_id()

            # For Linux, we'll leave drive_serial empty for now (can be added later)
            drive_serial = ""

        else:
            # Unsupported OS
            print(f"Unsupported OS: {self.current_os}")
            cpu_info = f"Unsupported OS: {self.current_os}"
            system_uuid = str(uuid.getnode())
            drive_serial = ""

        # Clean up the strings to ensure consistency
        cpu_info = cpu_info.strip()
        system_uuid = system_uuid.strip()
        drive_serial = drive_serial.strip()
        
        # Combine all components (including drive serial for Windows)
        hardware_info = cpu_info + system_uuid + drive_serial
        
        return hardware_info


    # IMPORTANT FOR DAN
    def generate_device_id(self):
        # Check if we're in frozen mode
        hardware_info = self.get_hardware_info()
        
        # Ensure consistent encoding
        hardware_info_bytes = hardware_info.encode('utf-8')
        device_id = hashlib.sha256(hardware_info_bytes).hexdigest()
        
        return device_id


    def compare_id(self, original_id, signed_id):
            # Load public key from PEM file
            pem_path = os.path.join(self.parent.settings_manager.data_dir, "shooshk.pem")
            with open(pem_path, "rb") as pem_file:
                public_pem = pem_file.read()

            # Convert the hexadecimal signature into bytes
            signature = bytes.fromhex(signed_id)

            # Determine library filename based on the operating system
            if sys.platform.startswith("linux"):
                lib_filename = "shoosh.so"
            else:
                lib_filename = "shoosh.dll"
            
            lib_path = os.path.join(self.parent.settings_manager.data_dir, lib_filename)
            
            # Load the shared library
            lib = ctypes.CDLL(lib_path)

            # Set up function signatures
            lib.load_public_key_from_mem.argtypes = [c_char_p, c_size_t]
            lib.load_public_key_from_mem.restype  = c_void_p  # Returns EVP_PKEY*
            lib.compare_id.argtypes = [c_char_p, POINTER(c_ubyte), c_size_t, c_void_p]
            lib.compare_id.restype  = c_bool

            # Load the public PEM into an EVP_PKEY*
            public_key_ptr = lib.load_public_key_from_mem(public_pem, len(public_pem))
            if not public_key_ptr:
                raise ValueError("Failed to load public key into EVP_PKEY*.")

            # Prepare signature buffer
            sig_len = len(signature)
            SignatureArrayType = c_ubyte * sig_len
            signature_array = SignatureArrayType(*signature)

            # Encode the original ID and call compare_id
            orig_id_bytes = original_id.encode("utf-8")
            result = lib.compare_id(orig_id_bytes, signature_array, sig_len, public_key_ptr)
            return result


    def get_EinTzofia_path(self):
        # get path of this script/frozen exe(or linux comparable)
        try:
            if getattr(sys, 'frozen', False):
                application_path = sys.executable   # path of the frozen exe
            else:
                application_path = __file__
            
            # go to parent dir
            base_dir = os.path.dirname(application_path)
            base_dir = os.path.dirname(base_dir)
            EinTzofia_dir_path = os.path.join(base_dir, 'EinTzofia')

            # get the only exe (or linux equivalent) file in the EinTzofia folder
            for filename in os.listdir(EinTzofia_dir_path):
                # and contains EinTzofia in it name
                if filename.endswith(self.executable_extension) and "EinTzofia" in filename:
                    return os.path.join(EinTzofia_dir_path, filename)
                

        except Exception as e:
            print(f"Error getting EinTzofia path: {e}")
            return ''

    def get_temp_dir_path(self):
        EinTzofia_dir_path = os.path.dirname(self.parent.settings['File_Path'])
        temp_dir_path = os.path.join(EinTzofia_dir_path, '_internal')
        temp_dir_path = os.path.join(temp_dir_path, 'temp')
        return temp_dir_path
    
    def get_data_dir_path(self):
        EinTzofia_dir_path = os.path.dirname(self.parent.settings['File_Path'])
        data_dir_path = os.path.join(EinTzofia_dir_path, '_internal')
        data_dir_path = os.path.join(data_dir_path, 'data')
        return data_dir_path

    def get_folder_contents(self, folder_path):
        """
        Returns a list of all files and folders (first level only) in the specified folder.
        
        Args:
            folder_path (str): Path to the folder to list contents of
            
        Returns:
            list: List of file and folder names in the specified folder, or empty list if folder doesn't exist
        """
        try:
            # Check if folder exists
            if not os.path.exists(folder_path):
                print(f"Folder not found at: {folder_path}")
                return []
            
            # Get all contents (files and directories) at first level only
            contents = []
            for item in os.listdir(folder_path):
                contents.append(item)
            
            print(f"Found {len(contents)} items in folder {folder_path}: {contents}")
            return contents
            
        except Exception as e:
            print(f"Error getting folder contents from {folder_path}: {e}")
            return []

    def get_eintzofia_internal_contents(self):
        """
        Returns a list of all files and folders (first level only) in the _internal folder 
        within the EinTzofia directory.
        
        Returns:
            list: List of file and folder names in _internal folder, or empty list if folder doesn't exist
        """
        try:
            # Get EinTzofia directory path
            EinTzofia_dir_path = os.path.dirname(self.parent.settings['File_Path'])
            
            # Construct path to _internal folder
            internal_folder_path = os.path.join(EinTzofia_dir_path, '_internal')
            
            # Use the generic method to get folder contents
            return self.get_folder_contents(internal_folder_path)
            
        except Exception as e:
            print(f"Error getting _internal folder contents: {e}")
            return []

    def get_eintzofia_data_contents(self):
        """
        Returns a list of all files and folders (first level only) in the data folder 
        within the EinTzofia _internal directory.
        
        Returns:
            list: List of file and folder names in data folder, or empty list if folder doesn't exist
        """
        try:
            # Get the data folder path using existing method
            data_folder_path = self.get_data_dir_path()
            
            # Use the generic method to get folder contents
            return self.get_folder_contents(data_folder_path)
            
        except Exception as e:
            print(f"Error getting data folder contents: {e}")
            return []

    def find_missing_eintzofia_contents(self, manifest):
        try:
            manifest = manifest["manifest"]
            internal_contents = self.get_eintzofia_internal_contents()
            data_contents = self.get_eintzofia_data_contents()
            manifest_internal_contents = manifest["_internal"]
            manifest_data_contents = manifest["data"]

            missing_internal = list(set(manifest_internal_contents).difference(set(internal_contents)))
            missing_data = list(set(manifest_data_contents).difference(set(data_contents)))
            return missing_internal, missing_data
        except Exception as e:
            print(f"Error finding missing EinTzofia contents: {e}")
            return [], []

    def _get_deterministic_system_id(self):
        """
        Get a deterministic system ID that both apps will compute identically.
        This ensures consistency when /etc/machine-id is not accessible.
        Uses hardware-based identifiers that don't change.
        """
        try:
            # Method 1: Try DMI UUID (same as Windows motherboard UUID)
            try:
                with open("/sys/class/dmi/id/product_uuid", "r") as f:
                    dmi_uuid = f.read().strip()
                    print(f"Using DMI UUID as deterministic ID: {dmi_uuid}")
                    return dmi_uuid
            except (FileNotFoundError, PermissionError) as e:
                print(f"DMI UUID not available: {e}")
            
            # Method 2: Create deterministic ID from hostname + MAC address
            import socket
            
            # Get hostname (should be same for both apps)
            hostname = socket.gethostname()
            
            # Get MAC address (should be same for both apps)
            mac_address = str(uuid.getnode())
            
            # Combine hostname and MAC address deterministically
            combined_info = f"EinTzofia-{hostname}-{mac_address}"
            
            # Create deterministic hash (both apps will compute same result)
            deterministic_id = hashlib.sha256(combined_info.encode()).hexdigest()[:32]
            
            print(f"Using hostname+MAC deterministic ID: {deterministic_id}")
            print(f"  Based on hostname: {hostname}")
            print(f"  Based on MAC: {mac_address}")
            
            return deterministic_id
            
        except Exception as e:
            print(f"Failed to create deterministic system ID: {e}")
            # Ultimate fallback - use just hostname-based deterministic value
            import socket
            hostname = socket.gethostname()
            fallback_id = hashlib.sha256(f"EinTzofia-{hostname}".encode()).hexdigest()[:32]
            print(f"Using hostname-only fallback ID: {fallback_id}")
            return fallback_id

    def get_monitor_dir_path(self):
        '''
        # Check if we're running as a frozen bundle or as a script
        if getattr(sys, 'frozen', False):
            # If frozen (executable), get the directory of the executable
            base_dir = os.path.dirname(sys.executable)
        else:
            # If running as a script, use the current file's path
            base_dir = os.path.dirname(os.path.abspath(__file__))
            # The monitor directory is where this script is located
        
        # Convert to absolute path
        print("DEBUG Monitor dir path:", base_dir)
        return base_dir'''
        if getattr(sys, 'frozen', False):
            # Running as PyInstaller executable
            return Path(sys.executable).parent
        else:
            # Development mode - return project root
            # This file is in monitor/utils/, so go up 2 levels to get project root
            return Path(__file__).parent.parent.parent

    def zip_folder(self, folder_path):
        """
        Creates a zip file from the given folder and returns the path to the temporary zip file.
        """
        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix='.zip') as tmp_zip:
                temp_zip_path = tmp_zip.name

            with zipfile.ZipFile(temp_zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for root, dirs, files in os.walk(folder_path):
                    for file in files:
                        abs_file_path = os.path.join(root, file)
                        rel_path = os.path.relpath(abs_file_path, os.path.join(folder_path, '..'))
                        zipf.write(abs_file_path, rel_path)

            return temp_zip_path
        except Exception as e:
            print("Failed zipping folder:", e)
            return None

    def delete_old_exe_file(self, path):
        """
        given a path, keep only the latest exe file in the path(folder)
        """
        # Ensure the path exists
        if not os.path.exists(path):
            raise FileNotFoundError(f"The path '{path}' does not exist.")

        # Get the list of files in the folder
        files = os.listdir(path)

        # Filter the list to include only exe files
        exe_files = [f for f in files if f.endswith('.exe')]

        # Sort the list of exe files by modification time

        exe_files.sort(key=lambda x: os.path.getmtime(os.path.join(path, x)))

     
        # Keep the latest exe file
        for i in range(len(exe_files) - 1):
            self.delete_file(os.path.join(path, exe_files[i]))

        return os.path.join(path, exe_files[-1])

    def create_file_shortcut(self, file_path):
        """
        create a shortcut file of a file given by its path (works for Windows and Linux)
        The shortcut is created in the same directory as the file_path.
        """
        if not os.path.exists(file_path):
            print(f"File not found: {file_path}")
            return None

        directory = os.path.dirname(file_path)
        base_name = os.path.basename(file_path)

        if self.current_os == "Windows":
            try:
                shell = Dispatch('WScript.Shell')
                # Shortcut file will be placed in the same directory with .lnk extension
                shortcut_path = os.path.join(directory, base_name + ".lnk")
                shortcut = shell.CreateShortcut(shortcut_path)
                shortcut.TargetPath = file_path
                shortcut.WorkingDirectory = directory
                shortcut.IconLocation = file_path
                shortcut.save()
                print(f"Windows shortcut created at: {shortcut_path}")
                return shortcut_path
            except Exception as e:
                print(f"Failed to create Windows shortcut: {e}")
                return None
        elif self.current_os == "Linux":
            try:
                # Create a .desktop file in the same directory.
                shortcut_path = os.path.join(directory, base_name + ".desktop")
                with open(shortcut_path, "w") as f:
                    f.write("[Desktop Entry]\n")
                    f.write("Type=Application\n")
                    f.write(f"Name={base_name}\n")
                    f.write(f"Exec={file_path}\n")
                    f.write(f"Path={directory}\n")
                    f.write("Terminal=true\n")
                os.chmod(shortcut_path, 0o755)
                print(f"Linux shortcut created at: {shortcut_path}")
                return shortcut_path
            except Exception as e:
                print(f"Failed to create Linux shortcut: {e}")
                return None
        else:
            print(f"Unsupported OS for creating shortcuts: {self.current_os}")
            return None


    def move_file_to_location(self,file_path,location):
        """
        move a file from its current location to a new location
        """
        try:
            shutil.move(file_path, location)
            print(f"File {file_path} has been moved to {location}")
        except FileNotFoundError:
            print(f"File {file_path} not found.")
        except PermissionError:
            print(f"Permission denied: unable to move {file_path}.")
        except Exception as e:
            print(f"Error moving file {file_path}: {e}")


    def get_path_to_startup_folder(self):
        """
        returns the path to the startup folder of the current OS
        """
        if self.current_os == "Windows":
            return os.path.join(os.getenv('APPDATA'), 'Microsoft', 'Windows', 'Start Menu', 'Programs', 'Startup')
        elif self.current_os == "Linux":
            return os.path.expanduser('~/.config/autostart')
        else:
            print(f"Unsupported OS for startup folder: {self.current_os}")
            return None


    def delete_old_shortcut(self,folder):
        """
        deletes the oldest shortcut file at the folder, that has "monitor" in its name 
        """
        # Ensure the folder exists
        if not os.path.exists(folder):
            raise FileNotFoundError(f"The folder '{folder}' does not exist.")

        # Filter the list to include only shortcut files
        shortcut_files = [f for f in os.listdir(folder) if f.endswith('.lnk')]

        # Sort the list of shortcut files by modification time
        shortcut_files.sort(key=lambda x: os.path.getmtime(os.path.join(folder, x)))

        # Keep the latest shortcut file
        for i in range(len(shortcut_files) - 1):
            self.delete_file(os.path.join(folder, shortcut_files[i]))

        return os.path.join(folder, shortcut_files[-1])

    def find_monitor_executable(self, directory):
        """
        Find the monitor executable file in the specified directory
        
        Args:
            directory: The directory to search in
            
        Returns:
            Path to the monitor executable file, or None if not found
        """
        print(f"Searching for monitor executable in {directory}")
        
        if self.current_os == "Windows":
            # Look for .exe files that might be the monitor executable
            for file in os.listdir(directory):
                if file.lower().endswith('.exe') and 'monitor' in file.lower():
                    found_path = os.path.join(directory, file)
                    print(f"Found monitor executable: {found_path}")
                    return found_path
        else:
            # For Linux, look for executable files
            for file in os.listdir(directory):
                file_path = os.path.join(directory, file)
                if os.path.isfile(file_path) and os.access(file_path, os.X_OK) and 'monitor' in file.lower():
                    print(f"Found monitor executable: {file_path}")
                    return file_path
        
        print(f"Monitor executable not found in {directory}")
        return None
        
    def create_dated_shortcut(self, file_path):
        """
        Create a shortcut with the current date in the name
        Format: Monitor_DD-MM-YY
        
        Args:
            file_path: Path to the file for which to create a shortcut
            
        Returns:
            Path to the created shortcut, or None if creation failed
        """
        if not os.path.exists(file_path):
            print(f"File not found: {file_path}")
            return None
            
        # Get current date in DD-MM-YY format
        current_date = datetime.now().strftime('%d-%m-%y')
        
        # Create a base name for the shortcut
        base_name = f"Monitor_{current_date}"
        
        # Get directory where the executable is located
        directory = os.path.dirname(file_path)
        
        print(f"Creating dated shortcut for {file_path} with name {base_name}")
        
        if self.current_os == "Windows":
            try:
                # Import Dispatch here to ensure it's available
                from win32com.client import Dispatch
                
                shell = Dispatch('WScript.Shell')
                shortcut_path = os.path.join(directory, f"{base_name}.lnk")
                shortcut = shell.CreateShortcut(shortcut_path)
                shortcut.TargetPath = file_path
                shortcut.WorkingDirectory = directory
                shortcut.IconLocation = file_path
                shortcut.save()
                print(f"Windows shortcut created at: {shortcut_path}")
                return shortcut_path
            except Exception as e:
                print(f"Failed to create Windows shortcut: {e}")
                return None
        elif self.current_os == "Linux":
            try:
                shortcut_path = os.path.join(directory, f"{base_name}.desktop")
                with open(shortcut_path, "w") as f:
                    f.write("[Desktop Entry]\n")
                    f.write("Type=Application\n")
                    f.write(f"Name={base_name}\n")
                    f.write(f"Exec={file_path}\n")
                    f.write(f"Path={directory}\n")
                    f.write("Terminal=true\n")
                os.chmod(shortcut_path, 0o755)
                print(f"Linux shortcut created at: {shortcut_path}")
                return shortcut_path
            except Exception as e:
                print(f"Failed to create Linux shortcut: {e}")
                return None
        else:
            print(f"Unsupported OS for creating shortcuts: {self.current_os}")
            return None
            
    def create_preserve_name_shortcut(self, file_path):
        print(f"Attempting to create shortcut for file: {file_path}")
        if not os.path.exists(file_path):
            print(f"File not found: {file_path}")
            return None

        file_path = os.path.normpath(os.path.abspath(str(file_path)))
        directory = os.path.dirname(file_path)
        base_name = os.path.splitext(os.path.basename(file_path))[0]
        shortcut_path = os.path.join(directory, f"{base_name}.lnk")

        print(f"Creating shortcut for {file_path} with preserved name {base_name}")

        if self.current_os == "Windows":
            try:
                def ps_escape(value):
                    return str(value).replace("'", "''")

                file_path_ps = ps_escape(file_path)
                directory_ps = ps_escape(directory)
                shortcut_path_ps = ps_escape(shortcut_path)

                ps_script = f"""
$WshShell = New-Object -ComObject WScript.Shell
$Shortcut = $WshShell.CreateShortcut('{shortcut_path_ps}')
$Shortcut.TargetPath = '{file_path_ps}'
$Shortcut.WorkingDirectory = '{directory_ps}'
$Shortcut.IconLocation = '{file_path_ps}'
$Shortcut.Save()
"""

                result = subprocess.run(
                    ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", ps_script],
                    capture_output=True,
                    text=True
                )

                print("DEBUG PowerShell return code:", result.returncode)
                print("DEBUG PowerShell stdout:", result.stdout)
                print("DEBUG PowerShell stderr:", result.stderr)

                if result.returncode == 0 and os.path.exists(shortcut_path):
                    print(f"Windows shortcut created at: {shortcut_path}")
                    return shortcut_path

                print("Failed to create Windows shortcut via PowerShell")
                return None

            except Exception as e:
                print(f"Failed to create Windows shortcut via PowerShell: {e}")
                return None

        elif self.current_os == "Linux":
            try:
                shortcut_path = os.path.join(directory, f"{base_name}.desktop")

                exec_command = f"/bin/bash -c \"cd '{directory}' && './{os.path.basename(file_path)}'\""

                with open(shortcut_path, "w") as f:
                    f.write("[Desktop Entry]\n")
                    f.write("Type=Application\n")
                    f.write(f"Name={base_name}\n")
                    f.write(f"Exec={exec_command}\n")
                    f.write(f"Path={directory}\n")
                    f.write("Terminal=true\n")
                    f.write("StartupNotify=false\n")
                    f.write("X-GNOME-Autostart-enabled=true\n")

                os.chmod(shortcut_path, 0o755)
                print(f"Linux shortcut created at: {shortcut_path}")
                return shortcut_path

            except Exception as e:
                print(f"Failed to create Linux shortcut: {e}")
                return None

        else:
            print(f"Unsupported OS for creating shortcuts: {self.current_os}")
            return None
            
    def create_shortcut_and_move_to_startup(self, file_path):
        """
        Creates a shortcut for the given file with the same name as the executable
        and moves it to the startup folder
        
        Args:
            file_path: Path to the file for which to create a shortcut
            
        Returns:
            Path to the shortcut in the startup folder, or None if operation failed
        """
        if not os.path.exists(file_path):
            print(f"File not found: {file_path}")
            return None
            
        # Create shortcut with preserved name
        shortcut_path = self.create_preserve_name_shortcut(file_path)
        if not shortcut_path:
            return None
            
        # Get startup folder
        startup_folder = self.get_path_to_startup_folder()
        if not startup_folder:
            print("Could not determine startup folder")
            return None
            
        # Copy shortcut to startup folder
        shortcut_name = os.path.basename(shortcut_path)
        startup_shortcut_path = os.path.join(startup_folder, shortcut_name)
        
        try:
            shutil.copy2(shortcut_path, startup_shortcut_path)
            print(f"Shortcut moved to startup folder: {startup_shortcut_path}")
            
            # Clean up original shortcut
            os.remove(shortcut_path)
            print(f"Deleted original shortcut: {shortcut_path}")
            
            return startup_shortcut_path
        except Exception as e:
            print(f"Error moving shortcut to startup folder: {e}")
            return None




    # def compare_id(self, original_id, signed_id):
    #         # Load public key from PEM file
    #         pem_path = os.path.join(self.parent.settings_manager.data_dir, "shooshk.pem")
    #         with open(pem_path, "rb") as pem_file:
    #             public_pem = pem_file.read()

    #         # Convert the hexadecimal signature into bytes
    #         signature = bytes.fromhex(signed_id)

    #         # Determine library filename based on the operating system
    #         if sys.platform.startswith("linux"):
    #             lib_filename = "shoosh.so"
    #         else:
    #             lib_filename = "shoosh.dll"
            
    #         lib_path = os.path.join(self.parent.settings_manager.data_dir, lib_filename)
            
    #         # Load the shared library
    #         lib = ctypes.CDLL(lib_path)

    #         # Set up function signatures
    #         lib.load_public_key_from_mem.argtypes = [c_char_p, c_size_t]
    #         lib.load_public_key_from_mem.restype  = c_void_p  # Returns EVP_PKEY*
    #         lib.compare_id.argtypes = [c_char_p, POINTER(c_ubyte), c_size_t, c_void_p]
    #         lib.compare_id.restype  = c_bool

    #         # Load the public PEM into an EVP_PKEY*
    #         public_key_ptr = lib.load_public_key_from_mem(public_pem, len(public_pem))
    #         if not public_key_ptr:
    #             raise ValueError("Failed to load public key into EVP_PKEY*.")

    #         # Prepare signature buffer
    #         sig_len = len(signature)
    #         SignatureArrayType = c_ubyte * sig_len
    #         signature_array = SignatureArrayType(*signature)

    #         # Encode the original ID and call compare_id
    #         orig_id_bytes = original_id.encode("utf-8")
    #         result = lib.compare_id(orig_id_bytes, signature_array, sig_len, public_key_ptr)
    #         return result


if __name__ == '__main__':
    osM = os_manager(None)
    device_id = osM.generate_device_id()
    print(f"Device ID: {device_id}")


