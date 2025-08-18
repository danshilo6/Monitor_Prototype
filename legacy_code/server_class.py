import aiohttp
import os
import requests
import zipfile
import tempfile
import traceback
import pandas as pd
import shutil
import pickle
from datetime import datetime
try:
    from .os_class import os_manager  # package relative (frozen & normal)
except ImportError:
    from os_class import os_manager   # fallback when run standalone

class ServerManager:
    
    def __init__(self,parent = None) -> None:
        self.parent = parent
        self.os_manager = os_manager
        #check if ran as unfrozen code
        if not os.path.exists(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'frozen')):
            self.base_url = 'http://127.0.0.1:5000'
        else:
            self.base_url = 'http://ec2-16-171-143-39.eu-north-1.compute.amazonaws.com:5000'



        if self.base_url == 'http://127.0.0.1:5000':
            print("DEBUG: SENDING LOCALLY")
        else:
            print("DEBUG: SENDING TO SERVER")
    
    def upload_configuration(self):
        temp_dir_path = self.parent.osManager.get_temp_dir_path()
        location = self.parent.settings['Location']
        upload_dir_path =  os.path.join(os.path.dirname(temp_dir_path), location)
        
        self.parent.osManager.copy_folder_structure(temp_dir_path,upload_dir_path)
        zipped_file_path = self.parent.osManager.zip_folder(upload_dir_path)
        self.upload_zip_file(zipped_file_path)
        self.parent.osManager.delete_folder_by_path(upload_dir_path)   

    def upload_zip_file(self, zip_path):
        """
        Uploads the specified zip file to the server and deletes the file afterwards.
        """
        server_ip = 'ec2-16-171-143-39.eu-north-1.compute.amazonaws.com'
        server_port = '5000'
        server_url = f'http://{server_ip}:{server_port}/upload_folder_new'

        try:
            with open(zip_path, 'rb') as zip_file:
                files = {'file': ('folder.zip', zip_file)}
                data = {'device_id': self.parent.osManager.generate_device_id()}
                response = requests.post(server_url, files=files, data=data)

            os.unlink(zip_path)
            return response.json()
        except Exception as e:
            print("Failed uploading file:", e)
            return None          

    # IMPORTANT FOR DAN
    def pulse_to_server(self,password = '',return_ID = False):     
        
        # initialize download flags
        eintzofia_download = False
        monitor_download = False

        server_url = f"{self.base_url}/pulse"
        # fetch location and device_id
        location = self.parent.settings['Location']
        device_id = self.parent.osManager.generate_device_id()
        print(f'Pulsing to server for PC ID: {device_id}')
        print('ID:    ',device_id)
        
        try:
            response = requests.post(server_url, json={'location': location,'password':password,'device_id':device_id,'return_ID':return_ID,'version':self.parent.VERSION})
            data = response.json()
            if response.status_code == 200:
                print(f'Pulse sent successfully for PC ID: {location}')
                correct_password = True if data['correct_password'] == "True" else False
                download_files = data['download_files']

                if isinstance(download_files,dict):
                    if download_files['eintzofia'] == "True" or download_files['eintzofia'] == True:
                        eintzofia_download = True
                    if download_files['monitor'] == "True" or download_files['monitor'] == True:
                        monitor_download = True
                else:
                    if download_files == "True" or download_files == True:
                        monitor_download = True
                
                trasnformed_ID = data['transformed_ID']#.fromhex().decode('utf-8')
                download_files = {
                    'eintzofia':eintzofia_download,
                    'monitor':monitor_download
                }
        
                return correct_password,download_files,trasnformed_ID
            else:
                print(f'Failed to send pulse: {response.status_code}')
                return "Fail","Fail", False
        except Exception as e:
            print(f'Error sending pulse: {str(e)}')
            return "Fail","Fail", False

    def get_configuration_options(self):
            # URL of your Flask server's /list_folders endpoint
        url = 'http://ec2-16-171-143-39.eu-north-1.compute.amazonaws.com:5000/list_folders'

        try:
            # Send a GET request to the server
            response = requests.get(url)
            
            # Check if the request was successful
            if response.status_code == 200:
                data = response.json()
                if data['status'] == 'success':
                    folders = data['folders']
                    return folders
                else:
                    print(f"Error: {data['message']}")
            else:
                print(f"Failed to connect to the server. Status code: {response.status_code}")
        except Exception as e:
            print(f"An error occurred: {e}")
    
    def download_configurations(self,folder_name):

        url = 'http://ec2-16-171-143-39.eu-north-1.compute.amazonaws.com:5000/download_folder'

        
        save_path = self.parent.osManager.get_temp_dir_path()
        save_path = os.path.join(save_path,"configurations.zip")
        
        payload = {'folder_name': folder_name}
        response = requests.post(url, data=payload,json={'device_id':self.device_id})

        if response.status_code == 200:
            with open(save_path, 'wb') as file:
                file.write(response.content)
            print(f'Folder "{folder_name}" downloaded and saved to "{save_path}".')
        else:
            print(f'Error downloading folder: {response.json()["message"]}')

    def set_download_files(self,locations,eintzofia_download = False,monitor_download = False):
        url = f"{self.base_url}/set_download_files"
        payload = {"locations": locations,"eintzofia_download":eintzofia_download,"monitor_download":monitor_download}
        try:
            response = requests.post(url, json=payload)
            if response.status_code == 200:
                result = response.json()
                print(f"Successfully updated {result['updated_count']} rows")
            else:
                print(f"Failed to update. Status code: {response.status_code}")
        except Exception as e:
            print(f"Error setting download files: {str(e)}")

    def check_id_exists_and_approved(self):
        # Construct the full URL for the check_id endpoint
        device_id = self.parent.osManager.generate_device_id()
        url = f"{self.base_url}/check_id"
        print(f"DEBUG: Checking ID: {device_id}")
        # Prepare the payload
        payload = {
            "device_id": device_id
        }
        
        try:
            # Send a POST request to the server
            response = requests.post(url, json=payload)
            
            # Check if the request was successful (status code 200)
            if response.status_code == 200:
                data = response.json()
                if data['status'] == 'success':
                    id_exists = True if data['exists'] == "True" else False
                    id_approved = True if data['approved'] == "True" else False
                    return id_exists,id_approved

                else:
                    return False,False
            else:
                return False,False
        
        except requests.exceptions.RequestException as e:
            print(f"Exception in check_id_exists of server_class: {e}")
            return False,False

    def remove_id_from_server(self,device_id,password):
        # Construct the full URL for the check_id endpoint
        url = f"{self.base_url}/remove_device"
        
        # Prepare the payload
        payload = {
            "device_id": device_id,
            "password":password
        }
        
        try:
            # Send a POST request to the server
            response = requests.post(url, json=payload)
            
            # Check if the request was successful (status code 200)
            data = response.json()
            if response.status_code == 200:
                print(data['message'])
            else:
                print(data['message'])
            return
        except requests.exceptions.RequestException as e:
            print(f"Exception in remove_id_from_server of server_class: {e}")
            return

    # IMPORTANT FOR DAN
    def send_email(self,subject,message,emails):

        url = f"{self.base_url}/send_email"
        device_id = self.parent.osManager.generate_device_id()

        for email in emails:
            # Prepare the payload
            payload = {
                'device_id':device_id,
                "to_email": email,
                "subject":subject,
                'message':message
            }


            try:
                response = requests.post(url, json=payload)
            
            except Exception as e:
                print("error",e)

    async def download_monitor_files(self):
        # Get the monitor directory path where files will be saved
        save_path = self.parent.osManager.get_monitor_dir_path()
        # Construct the URL to request the monitor file from the server
        url = f"{self.base_url}/send_monitor_file"
        try:
            # Create an asynchronous HTTP session
            async with aiohttp.ClientSession() as session:
                print("Monitor download started")
                # Send a POST request to the server to download the monitor file
                async with session.post(url) as response:
                    # Check if the request was successful
                    if response.status == 200:
                        # Read the response's content (expected to be a zip file)
                        content = await response.read()
                        # Define the path where the zip file will be stored temporarily
                        zip_path = os.path.join(save_path, "monitor.zip")

                        print("DEBUG Zip path:", zip_path)

                        # Write the downloaded content to the zip file
                        with open(zip_path, "wb") as f:
                            f.write(content)
                        print(f"Monitor download completed: {zip_path}")
                        
                        # Extract the contents of the zip file into the monitor directory
                        self.parent.osManager.extract_file(zip_path, save_path)
                        print("Extracted monitor files")
                        
                        # Find the monitor executable in the extracted files
                        monitor_executable = self.parent.osManager.find_monitor_executable(save_path)
                        if monitor_executable:
                            print(f"Found monitor executable: {monitor_executable}")
                            
                            # Create a shortcut and move it to startup folder
                            startup_shortcut_path = self.parent.osManager.create_shortcut_and_move_to_startup(monitor_executable)
                            if startup_shortcut_path:
                                print(f"Created and moved shortcut to startup: {startup_shortcut_path}")
                                
                                # Delete older Monitor shortcuts
                                print("DEBUG: About to delete old Monitor shortcuts")
                                self.parent.osManager.delete_old_shortcuts("Monitor")
                                print("Deleted older Monitor shortcuts from startup folder")
                                
                                # Delete the zip file after extraction to clean up
                                if os.path.exists(zip_path):
                                    os.remove(zip_path)
                                    print("Deleted monitor.zip after extraction")
                                
                                # Restart the PC to apply changes
                                print("All operations completed successfully. Restarting PC...")
                                self.parent.osManager.restart_pc()
                                return True
                        
                        # Delete the zip file after extraction to clean up
                        if os.path.exists(zip_path):
                            os.remove(zip_path)
                            print("Deleted monitor.zip after extraction")
                        return True
                    else:
                        # Log failure details if the response status is not 200
                        print(f"Monitor download failed. Status code: {response.status}")
                        print(f"Response text: {await response.text()}")
                        return False
        except Exception as e:
            # Handle any exceptions that occur during the download and extraction process
            print(f"Error during monitor download and extraction: {str(e)}")
            print("Traceback:")
            print(traceback.format_exc())
            return False
            
    async def download_exefiles(self,delete_old_file = False):
        
        save_path = self.parent.settings['File_Path']
        save_path = os.path.dirname(save_path)

        url = f"{self.base_url}/download_exefiles"
        
        try:
            async with aiohttp.ClientSession() as session:
                print("EinTzofia download started")
                async with session.get(url) as response:
                    if response.status == 200:
                        content = await response.read()
                        zip_path = os.path.join(save_path, "exefiles.zip")
                        with open(zip_path, "wb") as f:
                            f.write(content)
                        print(f"Download completed: {zip_path}")
                        
                        eintzofia_file_path = self.parent.osManager.extract_file(zip_path,save_path)
                        print("extracted files")


                        # Update EinTzofiaMonitor to use the new exe files
                        self.parent.settings['File_Path'] = eintzofia_file_path
                        self.parent.write_state_to_file()

                        # Delete the zip file after extraction to clean up
                        self.parent.osManager.delete_file(zip_path)
                        
                        # Restart the PC to apply changes
                        self.parent.osManager.restart_pc()
                        
                    else:
                        print(f"Download failed. Status code: {response.status}")
                        print(f"Response text: {await response.text()}")
        except Exception as e:
            print(f"Error during download and extraction: {str(e)}")
            print("Traceback:")
            print(traceback.format_exc())

    def send_SMS(self,message):

        url = f"{self.base_url}/send_sms"
        device_id = self.parent.osManager.generate_device_id()
        location = self.parent.settings['Location']
        to_phone = self.parent.settings['Phone_Number']
        # Prepare the payload
        payload = {
            'device_id':device_id,
            'message':message,
            'to_phone': to_phone,
            'location': location
        }


        try:
            response = requests.post(url, json=payload)
        
        except Exception as e:
            print("error")

    def enable_alerts(self,device_id,password):
        
        url = f"{self.base_url}/enable_alerts"
        # Prepare the payload
        payload = {
            'device_id':device_id,
            'password' : password
        }


        try:
            response = requests.post(url, json=payload)
        
        except Exception as e:
            print("error")

    def disable_alerts(self,device_id,password):
        
        url = f"{self.base_url}/disable_alerts"

        # Prepare the payload
        payload = {
            'device_id':device_id,
            'password' : password
        }


        try:
            response = requests.post(url, json=payload)
            print(response)
        except Exception as e:
            print("error")

    def get_signed_ID(self,device_id):
        url = f"{self.base_url}/sign_id"

        # Prepare the payload
        payload = {
            'device_id':device_id,
            'password' : 'SignID321#@!'
        }
        try:
            response = requests.post(url, json=payload)
            if response.status_code == 200:
                # print the signed ID
                data = response.json()
                sign = data['signature']
                return response.json()
            else:
                return {'status': 'error', 'message': 'Failed to get signed ID'}
        except Exception as e:
            # print the error
            print("error",e)

    def get_server_state(self, password):
        """
        Retrieves the current state from the server and prints it in a readable format
        with full device IDs displayed.
        
        Args:
            password (str): The password required to access the state
        """
        url = f"{self.base_url}/get_state"
        
        # Prepare the payload
        payload = {
            'password': password
        }
        
        try:
            # Send request to server
            response = requests.post(url, json=payload)
            
            if response.status_code == 200:
                data = response.json()
                if data['status'] == 'success':
                    state_data = data['state']
                    
                    # Print table header
                    print("\n")
                    print("=" * 120)
                    print("SERVER STATE - DEVICE LIST")
                    print("=" * 120)
                    
                    # Print a summary table first - with shortened IDs
                    summary_rows = []
                    for idx in state_data['index']:
                        row = state_data['data'][idx]
                        summary_rows.append({
                            'id_short': idx[:8] + '...',
                            'location': row.get('location', ''),
                            'last_pulse': row.get('last_pulse', ''),
                            'approved': row.get('approved', ''),
                            'send_alerts': row.get('send_alerts', '')
                        })
                    
                    if summary_rows:
                        summary_df = pd.DataFrame(summary_rows)
                        # Sort by location for better readability
                        summary_df = summary_df.sort_values('location')
                        print(summary_df.to_string(index=False))
                    
                    print("\n")
                    print("=" * 120)
                    print("DETAILED DEVICE INFORMATION")
                    print("=" * 120)
                    
                    # Print detailed information for each device
                    for idx in state_data['index']:
                        print("\n")
                        print("-" * 120)
                        print(f"Device ID: {idx}")
                        print("-" * 120)
                        
                        # Get row data and format for display
                        row_data = state_data['data'][idx]
                        
                        # Create a more readable format with key-value pairs
                        for key, value in row_data.items():
                            print(f"{key.ljust(20)} : {value}")
                    
                    print("\n")
                    print("=" * 120)
                    
                    # Create a proper DataFrame for return value
                    df = pd.DataFrame(columns=state_data['columns'])
                    for idx in state_data['index']:
                        df.loc[idx] = state_data['data'][idx]
                    
                    return df
                else:
                    print(f"Error: {data['message']}")
            else:
                print(f"Request failed with status code: {response.status_code}")
                if response.text:
                    print(f"Response: {response.text}")
                    
        except Exception as e:
            print(f"Exception in get_server_state: {e}")
            traceback.print_exc()
            
        return None

    def download_logs_from_server(self, device_id):
        """
        Downloads log file for a specific device from the server.
        
        Args:
            device_id (str): The device ID to download logs for
            
        Returns:
            dict or None: Log data dictionary if successful, None if failed
        """
        url = f"{self.base_url}/download_logs/{device_id}"
        
        try:
            print(f"DEBUG: Downloading logs for device {device_id}")
            response = requests.get(url)
            
            if response.status_code == 200:
                # The server sends a JSON file, so we need to parse the content
                import json
                log_data = json.loads(response.content.decode('utf-8'))
                print(f"DEBUG: Successfully downloaded {log_data.get('log_count', 0)} logs for device {device_id}")
                return log_data
            elif response.status_code == 404:
                print(f"DEBUG: No logs found for device {device_id}")
                return None
            else:
                print(f"DEBUG: Failed to download logs. Status code: {response.status_code}")
                print(f"DEBUG: Response: {response.text}")
                return None
                
        except Exception as e:
            print(f"DEBUG: Exception in download_logs_from_server: {e}")
            traceback.print_exc()
            return None

    def download_camera_images(self, save_path=None):
        """
        Downloads all camera images from the server to a local folder
        
        Args:
            save_path (str, optional): Directory to save images. If None, saves to temp directory
        
        Returns:
            str: Path to the folder with downloaded images if successful, None if failed
        """
        url = f"{self.base_url}/download_all_images"
        
        try:
            # Set default save path if not provided
            if save_path is None:
                save_path = self.parent.osManager.get_temp_dir_path() if self.parent else tempfile.gettempdir()
            
            # Create images folder
            os.makedirs(save_path, exist_ok=True)
            
            print("DEBUG: Downloading camera images...")
            response = requests.get(url)
            
            if response.status_code == 200:
                # Save and extract ZIP file
                zip_path = os.path.join(save_path, "temp_images.zip")
                with open(zip_path, 'wb') as f:
                    f.write(response.content)
                
                # Extract images
                with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                    zip_ref.extractall(save_path)
                
                # Delete ZIP file
                os.remove(zip_path)
                
                print(f"DEBUG: Camera images downloaded to: {save_path}")
                return save_path
            else:
                print(f"DEBUG: Failed to download images. Status code: {response.status_code}")
                return None
                
        except Exception as e:
            print(f"DEBUG: Exception in download_camera_images: {e}")
            traceback.print_exc()
            return None

    def download_encrypted_model(self, device_id,password):
        print(f"DEBUG: Downloading encrypted model for device {device_id}")
        try:
            url = f"{self.base_url}/send_encrypted_model"
            payload = {
                'device_id': device_id,
                'password': password
            }
            response = requests.post(url, json=payload)
            data = response.json()
            if data['status'] == 'success':
                # get the zipped files and save them to current dir
                current_dir = os.path.dirname(os.path.abspath(__file__))
                zip_path = os.path.join(current_dir, 'encrypted_model.zip')
                
                # Decode base64 string back to bytes
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

                # Ensure relative import works inside packaged application
                try:
                    from .os_class import os_manager  # type: ignore
                except Exception:  # fallback when run as script directly
                    from os_class import os_manager  # type: ignore
            else:
                print(f"DEBUG: Failed to download encrypted model. Status code: {response.status_code}")
                print(f"DEBUG: Response: {response.text}")
                return None
        
        except Exception as e:
            print(f"DEBUG: Exception in download_encrypted_model: {e}")
            traceback.print_exc()
            return None

if __name__ == '__main__':
    OS_manager = os_manager()
    server = ServerManager()

    server.download_encrypted_model(device_id=OS_manager.generate_device_id(),password='M0mTyaNwsQ6Lqr8l')