import aiohttp
import os
import requests
import zipfile
import tempfile
import traceback
import stat
import pandas as pd
import shutil
import pickle
import json
import time
from datetime import datetime
import sys
import ctypes
from ctypes import c_char_p, c_size_t, c_void_p, POINTER, c_ubyte, c_bool
import platform
import re
from datetime import datetime
import uuid
import hashlib
import subprocess
import psutil
import base64

try:
    from .os_class import os_manager  # package relative (frozen & normal)
except ImportError:
    from os_class import os_manager   # fallback when run standalone

class ServerManager:
    
    def __init__(self,parent = None) -> None:
        self.parent = parent
        self.os_manager = os_manager
        #check if ran as unfrozen code
        #if not os.path.exists(os.path.join(os.path.dirname(os.path.abspath#(__file__)), 'frozen')):
        
        # local
        #self.base_url = 'http://127.0.0.1:5001'
        #else:

        # server
        #self.base_url = 'http://ec2-13-49-189-10.eu-north-1.compute.amazonaws.com:5000'

        # server_dan
        self.base_url = 'http://ec2-13-49-189-10.eu-north-1.compute.amazonaws.com:5001'
        
        # dev server_dan
        #self.base_url = 'http://ec2-13-53-187-0.eu-north-1.compute.amazonaws.com:5001'
    
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
        #server_ip = 'ec2-16-171-143-39.eu-north-1.compute.amazonaws.com'
        #server_port = '5000'
        #server_url = f'http://{server_ip}:{server_port}/upload_folder_new'
        server_url = f"{self.base_url}/upload_folder_new"

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
    def pulse_to_server(self,password = '',return_ID = False, devices=None, restart_history=None):     
        
        # initialize download flags
        eintzofia_download = False
        monitor_download = False
        model_download = False
        model_password = ''

        server_url = f"{self.base_url}/pulse"
        # fetch location and device_id
        location = self.parent.settings['Location']
        device_id = self.parent.osManager.generate_device_id()
        print(f'Pulsing to server {self.base_url} for PC ID: {device_id}')
        print(f'DEBUG: Sending monitor_version: {self.parent.MONITOR_VERSION}')
        print(f'DEBUG: Sending eintzofia_version: {self.parent.EINTZOFIA_VERSION}')
        
        # Prepare payload with all devices and restart history
        payload = {
            'location': location,
            'password': password,
            'device_id': device_id,
            'return_ID': return_ID,
            'monitor_version': self.parent.MONITOR_VERSION,
            'eintzofia_version': self.parent.EINTZOFIA_VERSION
        }
        
        # Add all devices if provided
        if devices:
            payload['devices'] = devices
            print(f'DEBUG: Sending {len(devices)} devices')
        
        # Add restart history if provided
        if restart_history:
            payload['restart_history'] = restart_history
            print(f'DEBUG: Sending {len(restart_history)} restart records')
        
        try:
            response = requests.post(server_url, json=payload, timeout=30)
            data = response.json()
            if response.status_code == 200:
                print(f'Pulse sent successfully for {location}')
                correct_password = True if data['correct_password'] == "True" else False
                download_files = data['download_files']

                if isinstance(download_files,dict):
                    if download_files['eintzofia'] == "True" or download_files['eintzofia'] == True:
                        eintzofia_download = True
                    if download_files['monitor'] == "True" or download_files['monitor'] == True:
                        monitor_download = True
                    if download_files['model'] == "True" or download_files['model'] == True:
                        model_download = True
                    if download_files['model_password']:
                        model_password = download_files['model_password']
                else:
                    if download_files == "True" or download_files == True:
                        monitor_download = True
                
                trasnformed_ID = data['transformed_ID']#.fromhex().decode('utf-8')
                download_files = {
                    'eintzofia':eintzofia_download,
                    'monitor': monitor_download,
                    'model': model_download,
                    'model_password': model_password
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
        # url = 'http://ec2-16-171-143-39.eu-north-1.compute.amazonaws.com:5000/list_folders'
        url = f"{self.base_url}/list_folders"

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

        # url = 'http://ec2-16-171-143-39.eu-north-1.compute.amazonaws.com:5000/download_folder'
        url = f"{self.base_url}/download_folder"
        
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

    def set_download_files(self,locations,eintzofia_download = False,monitor_download = False,model_download=False):
        url = f"{self.base_url}/set_download_files"
        payload = {"locations": locations,"eintzofia_download":eintzofia_download,"monitor_download":monitor_download, "model_download":model_download}
        try:
            response = requests.post(url, json=payload, timeout=30)
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
            response = requests.post(url, json=payload, timeout=30)
            
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

        success_count = 0
        total_emails =len(emails)

        for email in emails:
            # Prepare the payload
            payload = {
                'device_id':device_id,
                "to_email": email,
                "subject":subject,
                'message':message
            }


            try:
                response = requests.post(url, json=payload, timeout=30)
                print(f"Respone status: {response.status_code}")
                print(f"Respone text: {response.text}")
                if response.status_code == 200:
                    success_count += 1
                    print(f"notification for {email} sent successfuly to server")
                else:
                    print(f"failed to send notification for {email}")
            
            except Exception as e:
                print("error",e)
        return success_count == total_emails

    def send_email_debug(self):
        """
        Debug method to test email functionality with specific device ID and test emails.
        Uses hardcoded test values for debugging purposes.
        """
        # Hardcoded debug values
        debug_device_id = "2a07b5bc258822179bd48581852efc645209ac7014eacf95f6f50fe8f15777fe7a1ffea4fff8d2a89f7dcae439187059311dff26f08a64efafac42826d1f30d79443439ec47daba4adbce14f5cd809f4e743db439d633a10f4b9b8d185e0bf2fc37df41d4f5fe43b86129b35594962cdac00cca0ea625e7d44c46e1738cc0386ffcb5dd85b6f0060acc6c5f0f29561ac1ac04c88f6f7b2ae6a4fbd59b57439a28e8e5c2f60200609a85706890bd25f4cb3182283e434f02dd10eba51fdeae08c46f7553e79c7f02ac2b0b80e62ecf69197161fa121cb73383f6f099b9733f0ade3da5eb5f5a8befaf7cab30cd187bec573a2bdc5aaa66adacd587f40366b53bd"
        debug_url = "http://ec2-13-49-189-10.eu-north-1.compute.amazonaws.com:5001"
        debug_emails = ["dan@bulltech.co.il", "asaf@bulltech.co.il"]
        
        url = f"{debug_url}/send_email"
        
        # Test email content
        subject = "Debug Test Email"
        message = "This is a test email from the send_email_debug method using the hardcoded device ID."
        
        success_count = 0
        total_emails = len(debug_emails)
        
        print(f"DEBUG: Testing email functionality with device ID: {debug_device_id[:20]}...")
        print(f"DEBUG: Using server URL: {debug_url}")
        print(f"DEBUG: Sending to {total_emails} recipients: {debug_emails}")
        
        for email in debug_emails:
            # Prepare the payload
            payload = {
                'device_id': debug_device_id,
                "to_email": email,
                "subject": subject,
                'message': message
            }
            
            try:
                print(f"DEBUG: Attempting to send email to {email}...")
                response = requests.post(url, json=payload, timeout=30)
                print(f"DEBUG: Response status: {response.status_code}")
                print(f"DEBUG: Response text: {response.text}")
                
                if response.status_code == 200:
                    success_count += 1
                    print(f"DEBUG: Email sent successfully to {email}")
                else:
                    print(f"DEBUG: Failed to send email to {email}")
                    
            except Exception as e:
                print(f"DEBUG: Error sending email to {email}: {str(e)}")
        
        print(f"DEBUG: Email test completed. {success_count}/{total_emails} emails sent successfully.")
        return success_count == total_emails

    async def download_monitor_files(self):
        # Get the monitor directory path where files will be saved
        save_path = self.parent.osManager.get_monitor_dir_path()
        # Construct the URL to request the monitor file from the server
        url = f"{self.base_url}/send_monitor_file"
        download_timeout = aiohttp.ClientTimeout(total=3600, connect=30)  # 1 hour total timeout

        try:
            # Create an asynchronous HTTP session
            async with aiohttp.ClientSession(timeout=download_timeout) as session:
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
                                #self.parent.osManager.restart_pc()
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
        download_timeout = aiohttp.ClientTimeout(total=3600, connect=30)  # 1 hour total 

        try:
            async with aiohttp.ClientSession(timeout=download_timeout) as session:
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
                        
                        # Set flag for manifest processing on next startup
                        print("DEBUG: Setting manifest processing flag for next startup")
                        self._set_manifest_processing_flag()
                        
                        # Restart the PC to apply changes
                        #   self.parent.osManager.restart_pc()
                        return True
                        
                    else:
                        print(f"Download failed. Status code: {response.status}")
                        print(f"Response text: {await response.text()}")
                        return False
        except Exception as e:
            print(f"Error during download and extraction: {str(e)}")
            print("Traceback:")
            print(traceback.format_exc())
            return False

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

    def get_eintzofia_manifest(self):
        """
        Retrieves the EinTzofia manifest from the server.
        
        Returns:
            dict or None: Manifest data if successful, None if failed
        """
        url = f"{self.base_url}/get_eintzofia_manifest"
        
        try:
            print("DEBUG: Requesting EinTzofia manifest from server")
            response = requests.get(url, timeout=30)
            
            if response.status_code == 200:
                manifest_data = response.json()
                print(f"DEBUG: Successfully retrieved EinTzofia manifest")
                return manifest_data
            else:
                print(f"DEBUG: Failed to get EinTzofia manifest. Status code: {response.status_code}")
                print(f"DEBUG: Response: {response.text}")
                return None
                
        except requests.exceptions.RequestException as e:
            print(f"DEBUG: Request exception in get_eintzofia_manifest: {e}")
            return None
        except Exception as e:
            print(f"DEBUG: Exception in get_eintzofia_manifest: {e}")
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

    async def download_encrypted_model(self, device_id, password):
        print(f"DEBUG: Downloading encrypted model for device {device_id}")
        
        url = f"{self.base_url}/send_encrypted_model"
        download_timeout = aiohttp.ClientTimeout(total=3600, connect=30)  # 1 hour total timeout
        
        payload = {
            'device_id': device_id,
            'password': password
        }
        
        try:
            async with aiohttp.ClientSession(timeout=download_timeout) as session:
                print("Encrypted model download started")
                async with session.post(url, json=payload) as response:
                    if response.status == 200:
                        # Server now sends the zip file directly, not JSON
                        content_type = response.headers.get('content-type', '')
                        if 'application/zip' not in content_type:
                            # If it's not a zip file, it might be an error response
                            try:
                                error_data = await response.json()
                                print(f"DEBUG: Server returned error: {error_data.get('message', 'Unknown error')}")
                                return False
                            except:
                                print(f"DEBUG: Unexpected response content type: {content_type}")
                                return False
                        
                        # Get save path and create zip file path
                        save_path = self.parent.osManager.get_data_dir_path()
                        current_dir = os.path.dirname(os.path.abspath(__file__))
                        zip_path = os.path.join(current_dir, f'encrypted_model_{device_id[:8]}.zip')
                        
                        # Read the zip file content directly
                        zip_content = await response.read()
                        file_size = len(zip_content)
                        print(f"DEBUG: Downloaded {file_size / (1024*1024):.2f} MB")
                        
                        # Save the zip file
                        with open(zip_path, 'wb') as f:
                            f.write(zip_content)
                        print(f"DEBUG: Encrypted model saved successfully to: {zip_path}")
                        
                        # Extract the zip file
                        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                            zip_ref.extractall(save_path)
                        print(f"DEBUG: Extracted encrypted model to: {save_path}")
                        
                        # Clean up zip file
                        os.remove(zip_path)
                        print("DEBUG: Cleaned up temporary zip file")
                        return True
                        
                    else:
                        # Handle error responses
                        try:
                            error_data = await response.json()
                            print(f"DEBUG: Server error: {error_data.get('message', 'Unknown error')}")
                        except:
                            print(f"DEBUG: Download failed. Status code: {response.status}")
                            print(f"DEBUG: Response text: {await response.text()}")
                        return False
                        
        except Exception as e:
            print(f"DEBUG: Exception in download_encrypted_model: {e}")
            traceback.print_exc()
            return False

    def get_eintzofia_manifest(self):
        """
        Retrieves the EinTzofia manifest from the server.
        
        Returns:
            dict or None: Manifest data if successful, None if failed
        """
        url = f"{self.base_url}/get_eintzofia_manifest"
        
        try:
            print("DEBUG: Requesting EinTzofia manifest from server")
            response = requests.get(url, timeout=30)
            
            if response.status_code == 200:
                manifest_data = response.json()
                print(f"DEBUG: Successfully retrieved EinTzofia manifest")
                return manifest_data
            else:
                print(f"DEBUG: Failed to get EinTzofia manifest. Status code: {response.status_code}")
                print(f"DEBUG: Response: {response.text}")
                return None
                
        except requests.exceptions.RequestException as e:
            print(f"DEBUG: Request exception in get_eintzofia_manifest: {e}")
            return None
        except Exception as e:
            print(f"DEBUG: Exception in get_eintzofia_manifest: {e}")
            traceback.print_exc()
            return None

    def create_local_eintzofia_manifest(self):
        """
        Creates or updates a local manifest for EinTzofia by scanning the _internal, data, temp, icons, and styles folders.
        
        The manifest matches the server format with executable, _internal, data, temp, icons, and styles sections.
        Data folder is located inside _internal folder.
        Temp folder is located inside _internal folder.
        Icons folder is located at _internal/monitor/gui/icons.
        Styles folder is located at _internal/monitor/gui/styles.
        New items get a default version/date of "01-01-2000".
        
        Returns:
            dict or None: The created/updated manifest, or None if failed
        """
        try:
            print("DEBUG: Creating/updating local EinTzofia manifest")
            
            # Get paths
            eintzofia_root = os.path.dirname(self.parent.settings['File_Path'])
            internal_dir = os.path.join(eintzofia_root, '_internal')
            data_dir = os.path.join(internal_dir, 'data')  # data is inside _internal
            temp_dir = os.path.join(internal_dir, 'temp')  # temp is inside _internal
            icons_dir = os.path.join(internal_dir, 'monitor', 'gui', 'icons')  # icons path
            styles_dir = os.path.join(internal_dir, 'monitor', 'gui', 'styles')  # styles path
            
            # Save manifest to monitor's data folder
            monitor_base_dir = self.parent.osManager.get_monitor_dir_path()
            monitor_data_dir = os.path.join(monitor_base_dir, 'data')
            manifest_file = os.path.join(monitor_data_dir, 'eintzofia_manifest_local.json')
            
            # Default version/date for new items (January 1, 2000)
            default_date = "01-01-2000"
            
            # Load existing manifest if it exists
            existing_manifest = {}
            if os.path.exists(manifest_file):
                try:
                    with open(manifest_file, 'r') as f:
                        existing_manifest = json.load(f)
                    print(f"DEBUG: Loaded existing manifest with {len(existing_manifest)} sections")
                except (json.JSONDecodeError, IOError) as e:
                    print(f"DEBUG: Error reading existing manifest, creating new one: {e}")
                    existing_manifest = {}
            
            # Initialize manifest structure
            manifest = {
                "executable": [],
                "_internal": [],
                "data": [],
                "temp": [],
                "icons": [],
                "styles": []
            }
            
            # Helper function to create manifest entry
            def create_entry(name, existing_items):
                """Create manifest entry, preserving existing date or using default"""
                existing_entry = next((item for item in existing_items if item.get('name') == name), None)
                
                if existing_entry:
                    date = existing_entry.get('date', default_date)
                    return {
                        "name": name,
                        "version": date,
                        "date": date
                    }
                else:
                    print(f"DEBUG: New item found: {name}, assigning default date {default_date}")
                    return {
                        "name": name,
                        "version": default_date,
                        "date": default_date
                    }
            
            # Scan _internal folder (excluding data, temp, and monitor subfolders)
            print(f"DEBUG: Scanning _internal folder: {internal_dir}")
            existing_internal = existing_manifest.get("_internal", [])
            
            if os.path.exists(internal_dir):
                try:
                    for item in os.listdir(internal_dir):
                        # Skip the data, temp, and monitor folders - they're handled separately
                        if item not in ['data', 'temp', 'monitor']:
                            item_path = os.path.join(internal_dir, item)
                            if os.path.isdir(item_path) or os.path.isfile(item_path):
                                manifest["_internal"].append(create_entry(item, existing_internal))
                                print(f"DEBUG: Added _internal item: {item}")
                except Exception as e:
                    print(f"DEBUG: Error scanning _internal directory: {e}")
            else:
                print(f"DEBUG: _internal directory not found: {internal_dir}")
            
            # Scan data folder (inside _internal)
            print(f"DEBUG: Scanning data folder: {data_dir}")
            existing_data = existing_manifest.get("data", [])
            
            if os.path.exists(data_dir):
                try:
                    for item in os.listdir(data_dir):
                        item_path = os.path.join(data_dir, item)
                        if os.path.isdir(item_path) or os.path.isfile(item_path):
                            manifest["data"].append(create_entry(item, existing_data))
                            print(f"DEBUG: Added data item: {item}")
                except Exception as e:
                    print(f"DEBUG: Error scanning data directory: {e}")
            else:
                print(f"DEBUG: data directory not found: {data_dir}")
            
            # Scan temp folder (inside _internal)
            print(f"DEBUG: Scanning temp folder: {temp_dir}")
            existing_temp = existing_manifest.get("temp", [])
            
            if os.path.exists(temp_dir):
                try:
                    for item in os.listdir(temp_dir):
                        item_path = os.path.join(temp_dir, item)
                        if os.path.isdir(item_path) or os.path.isfile(item_path):
                            manifest["temp"].append(create_entry(item, existing_temp))
                            print(f"DEBUG: Added temp item: {item}")
                except Exception as e:
                    print(f"DEBUG: Error scanning temp directory: {e}")
            else:
                print(f"DEBUG: temp directory not found: {temp_dir}")
            
            # Scan icons folder (inside _internal/monitor/gui/icons)
            print(f"DEBUG: Scanning icons folder: {icons_dir}")
            existing_icons = existing_manifest.get("icons", [])
            
            if os.path.exists(icons_dir):
                try:
                    for item in os.listdir(icons_dir):
                        item_path = os.path.join(icons_dir, item)
                        if os.path.isdir(item_path) or os.path.isfile(item_path):
                            manifest["icons"].append(create_entry(item, existing_icons))
                            print(f"DEBUG: Added icons item: {item}")
                except Exception as e:
                    print(f"DEBUG: Error scanning icons directory: {e}")
            else:
                print(f"DEBUG: icons directory not found: {icons_dir}")
            
            # Scan styles folder (inside _internal/monitor/gui/styles)
            print(f"DEBUG: Scanning styles folder: {styles_dir}")
            existing_styles = existing_manifest.get("styles", [])
            
            if os.path.exists(styles_dir):
                try:
                    for item in os.listdir(styles_dir):
                        item_path = os.path.join(styles_dir, item)
                        if os.path.isdir(item_path) or os.path.isfile(item_path):
                            manifest["styles"].append(create_entry(item, existing_styles))
                            print(f"DEBUG: Added styles item: {item}")
                except Exception as e:
                    print(f"DEBUG: Error scanning styles directory: {e}")
            else:
                print(f"DEBUG: styles directory not found: {styles_dir}")
            
            # Save manifest to file
            try:
                os.makedirs(monitor_data_dir, exist_ok=True)
                
                with open(manifest_file, 'w') as f:
                    json.dump(manifest, f, indent=2)
                
                print(f"DEBUG: Local manifest saved to: {manifest_file}")
                print(f"DEBUG: Manifest contains: {len(manifest['executable'])} executables, "
                      f"{len(manifest['_internal'])} _internal items, {len(manifest['data'])} data items, "
                      f"{len(manifest['temp'])} temp items, {len(manifest['icons'])} icons items, "
                      f"{len(manifest['styles'])} styles items")
                
            except Exception as e:
                print(f"DEBUG: Error saving manifest file: {e}")
                return None
            
            return manifest
            
        except Exception as e:
            print(f"DEBUG: Exception in create_local_eintzofia_manifest: {e}")
            traceback.print_exc()
            return None

    def update_local_manifest_item(self, section, item_name, new_version, new_date=None):
        """
        Updates a specific item in the local manifest with new version information.
        
        Args:
            section (str): The manifest section ('executable', '_internal', or 'data')
            item_name (str): Name of the item to update
            new_version (str): New version to set
            new_date (str, optional): New date to set. If None, uses new_version
        
        Returns:
            bool: True if updated successfully, False if failed
        """
        try:
            # Use new_version as date if not provided
            if new_date is None:
                new_date = new_version
                
            # Get manifest file path
            monitor_base_dir = self.parent.osManager.get_monitor_dir_path()
            monitor_data_dir = os.path.join(monitor_base_dir, 'data')
            manifest_file = os.path.join(monitor_data_dir, 'eintzofia_manifest_local.json')
            
            # Load existing manifest
            if not os.path.exists(manifest_file):
                print(f"DEBUG: Manifest file not found: {manifest_file}")
                return False
                
            with open(manifest_file, 'r') as f:
                manifest = json.load(f)
            
            # Validate section
            if section not in manifest:
                print(f"DEBUG: Invalid section '{section}' in manifest")
                return False
            
            # Find and update the item
            item_found = False
            for item in manifest[section]:
                if item.get('name') == item_name:
                    item['version'] = new_version
                    item['date'] = new_date
                    item_found = True
                    print(f"DEBUG: Updated {section}/{item_name} to version {new_version}")
                    break
            
            if not item_found:
                print(f"DEBUG: Item '{item_name}' not found in section '{section}'")
                return False
            
            # Save updated manifest
            with open(manifest_file, 'w') as f:
                json.dump(manifest, f, indent=2)
                
            print(f"DEBUG: Manifest updated and saved successfully")
            return True
            
        except Exception as e:
            print(f"DEBUG: Exception in update_local_manifest_item: {e}")
            traceback.print_exc()
            return False

    def compare_eintzofia_manifests(self, server_manifest, local_manifest):
        """
        Compares server and local EinTzofia manifests to find items that need updating.
        
        Args:
            server_manifest (dict): Manifest from server
            local_manifest (dict): Local manifest
            
        Returns:
            dict: Dictionary containing items that need updates, organized by section
        """
        try:
            print("DEBUG: Comparing server and local manifests")
            
            if not server_manifest or not local_manifest:
                print("DEBUG: Missing manifest data - server or local manifest is None")
                return None
            
            # Extract the actual manifest data from server response if needed
            if 'manifest' in server_manifest:
                server_data = server_manifest['manifest']
                print("DEBUG: Extracting manifest from server response")
            else:
                server_data = server_manifest
                print("DEBUG: Using server manifest directly")
            
            print(f"DEBUG: Server manifest keys: {list(server_data.keys())}")
            print(f"DEBUG: Local manifest keys: {list(local_manifest.keys())}")
            
            # Initialize result dictionary
            updates_needed = {
                "_internal": [],
                "data": [],
                "temp": [],
                "icons": [],
                "styles": []
            }
            
            # Helper function to parse date strings for comparison
            def parse_date(date_string):
                """Parse date string in DD-MM-YYYY format to datetime object"""
                try:
                    return datetime.strptime(date_string, "%d-%m-%Y")
                except ValueError:
                    try:
                        # Try DD-MM-YY format
                        return datetime.strptime(date_string, "%d-%m-%y")
                    except ValueError:
                        print(f"DEBUG: Could not parse date: {date_string}")
                        return datetime.min
            
            # Compare each section
            for section in ["_internal", "data", "temp", "icons", "styles"]:
                if section not in server_data:
                    print(f"DEBUG: Section '{section}' not found in server manifest")
                    continue
                    
                if section not in local_manifest:
                    print(f"DEBUG: Section '{section}' not found in local manifest")
                    continue
                
                print(f"DEBUG: Comparing {section} section")
                
                # Create lookup dictionary for local items
                local_items = {item['name']: item for item in local_manifest[section]}
                
                # Check each server item
                for server_item in server_data[section]:
                    server_name = server_item.get('name')
                    server_date = server_item.get('date')
                    server_version = server_item.get('version')
                    
                    if not server_name or not server_date:
                        print(f"DEBUG: Invalid server item - missing name or date: {server_item}")
                        continue
                    
                    # Check if item exists locally
                    local_item = local_items.get(server_name)
                    
                    if not local_item:
                        # Item not found locally - needs download
                        print(f"DEBUG: Item '{server_name}' not found in local {section}")
                        updates_needed[section].append({
                            'name': server_name,
                            'reason': 'missing_locally',
                            'server_version': server_version,
                            'server_date': server_date,
                            'local_version': None,
                            'local_date': None
                        })
                        continue
                    
                    # Item exists locally - compare dates
                    local_date = local_item.get('date')
                    local_version = local_item.get('version')
                    
                    if not local_date:
                        print(f"DEBUG: Local item '{server_name}' has no date - needs update")
                        updates_needed[section].append({
                            'name': server_name,
                            'reason': 'missing_local_date',
                            'server_version': server_version,
                            'server_date': server_date,
                            'local_version': local_version,
                            'local_date': local_date
                        })
                        continue
                    
                    # Compare dates
                    server_datetime = parse_date(server_date)
                    local_datetime = parse_date(local_date)
                    
                    if server_datetime > local_datetime:
                        print(f"DEBUG: Item '{server_name}' is newer on server ({server_date} > {local_date})")
                        updates_needed[section].append({
                            'name': server_name,
                            'reason': 'newer_version_available',
                            'server_version': server_version,
                            'server_date': server_date,
                            'local_version': local_version,
                            'local_date': local_date
                        })
                    else:
                        print(f"DEBUG: Item '{server_name}' is up to date (local: {local_date}, server: {server_date})")
            
            # Print summary
            total_updates = len(updates_needed["_internal"]) + len(updates_needed["data"]) + len(updates_needed["temp"]) + len(updates_needed["icons"]) + len(updates_needed["styles"])
            
            if total_updates > 0:
                print(f"\nDEBUG: === MANIFEST COMPARISON SUMMARY ===")
                print(f"DEBUG: Total items needing updates: {total_updates}")
                
                if updates_needed["_internal"]:
                    print(f"DEBUG: _internal items needing updates: {len(updates_needed['_internal'])}")
                    for item in updates_needed["_internal"]:
                        print(f"DEBUG:   - {item['name']} ({item['reason']})")
                
                if updates_needed["data"]:
                    print(f"DEBUG: data items needing updates: {len(updates_needed['data'])}")
                    for item in updates_needed["data"]:
                        print(f"DEBUG:   - {item['name']} ({item['reason']})")
                
                if updates_needed["temp"]:
                    print(f"DEBUG: temp items needing updates: {len(updates_needed['temp'])}")
                    for item in updates_needed["temp"]:
                        print(f"DEBUG:   - {item['name']} ({item['reason']})")
                
                if updates_needed["icons"]:
                    print(f"DEBUG: icons items needing updates: {len(updates_needed['icons'])}")
                    for item in updates_needed["icons"]:
                        print(f"DEBUG:   - {item['name']} ({item['reason']})")
                
                if updates_needed["styles"]:
                    print(f"DEBUG: styles items needing updates: {len(updates_needed['styles'])}")
                    for item in updates_needed["styles"]:
                        print(f"DEBUG:   - {item['name']} ({item['reason']})")
                
                print(f"DEBUG: =====================================\n")
            else:
                print("DEBUG: All items are up to date - no updates needed")
            
            return updates_needed
            
        except Exception as e:
            print(f"DEBUG: Exception in compare_eintzofia_manifests: {e}")
            traceback.print_exc()
            return None

    def _set_manifest_processing_flag(self):
        """Set config flag to process manifest on next monitor startup."""
        try:
            if hasattr(self.parent, 'config_service') and self.parent.config_service:
                self.parent.config_service.set("system", "process_manifest_on_startup", True)
                print("DEBUG: Manifest processing flag set in config")
                return True
            else:
                print("DEBUG: No config service available to set manifest flag")
                return False
        except Exception as e:
            print(f"DEBUG: Error setting manifest processing flag: {e}")
            return False

    def process_manifest_updates(self):
        """
        Process manifest updates by comparing server vs local and downloading needed files.
        Called on startup when manifest processing flag is set.
        
        Returns:
            bool: True if processing completed successfully, False otherwise
        """
        try:
            print("DEBUG: Starting manifest processing...")
            
            # Step 1: Get server manifest
            server_manifest = self.get_eintzofia_manifest()
            if not server_manifest:
                print("DEBUG: Failed to get server manifest")
                return False
            
            # Step 2: Create/update local manifest
            local_manifest = self.create_local_eintzofia_manifest()
            if not local_manifest:
                print("DEBUG: Failed to create local manifest")
                return False
            
            # Step 3: Compare manifests to find updates needed
            updates_needed = self.compare_eintzofia_manifests(server_manifest, local_manifest)
            if not updates_needed:
                print("DEBUG: Manifest comparison failed")
                return False
            
            # Step 4: Download and update files that need updating
            total_updates = len(updates_needed["_internal"]) + len(updates_needed["data"]) + len(updates_needed["temp"]) + len(updates_needed["icons"]) + len(updates_needed["styles"])
            if total_updates == 0:
                print("DEBUG: No manifest updates needed")
                return True
            
            print(f"DEBUG: Processing {total_updates} manifest updates...")
            successful_updates = 0
            
            # Process _internal updates
            for item in updates_needed["_internal"]:
                if self._download_and_update_manifest_item("_internal", item):
                    successful_updates += 1
            
            # Process data updates  
            for item in updates_needed["data"]:
                if self._download_and_update_manifest_item("data", item):
                    successful_updates += 1
            
            # Process temp updates
            for item in updates_needed["temp"]:
                if self._download_and_update_manifest_item("temp", item):
                    successful_updates += 1
            
            # Process icons updates
            for item in updates_needed["icons"]:
                if self._download_and_update_manifest_item("icons", item):
                    successful_updates += 1
            
            # Process styles updates
            for item in updates_needed["styles"]:
                if self._download_and_update_manifest_item("styles", item):
                    successful_updates += 1
            
            print(f"DEBUG: Manifest processing completed: {successful_updates}/{total_updates} updates successful")
            return successful_updates == total_updates
            
        except Exception as e:
            print(f"DEBUG: Exception in process_manifest_updates: {e}")
            traceback.print_exc()
            return False

    def _download_and_update_manifest_item(self, section, item_info):
        """
        Download a specific manifest item and update the local manifest.
        
        Args:
            section (str): '_internal' or 'data'
            item_info (dict): Item information from manifest comparison
        
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            item_name = item_info['name']
            server_version = item_info['server_version']
            
            print(f"DEBUG: Downloading {section}/{item_name}...")
            
            # Download the file using the server's download endpoint with retries
            success = self._download_manifest_file_with_retry(section, item_name)
            
            if success:
                # Update local manifest with new version
                self.update_local_manifest_item(section, item_name, server_version)
                print(f"DEBUG: Successfully updated {section}/{item_name}")
                return True
            else:
                print(f"DEBUG: Failed to download {section}/{item_name}")
                return False
                
        except Exception as e:
            print(f"DEBUG: Exception downloading {section}/{item_name}: {e}")
            return False

    def _download_manifest_file_with_retry(self, section, item_name, max_retries=3):
        """
        Download a specific file with retry logic and exponential backoff.
        
        Args:
            section (str): '_internal' or 'data'
            item_name (str): Name of the item to download
            max_retries (int): Maximum number of retry attempts
        
        Returns:
            bool: True if successful, False if all attempts failed
        """
        for attempt in range(max_retries):
            try:
                if attempt > 0:
                    print(f"DEBUG: Download attempt {attempt + 1}/{max_retries} for {item_name}")
                    
                success = self._download_manifest_file(section, item_name)
                if success:
                    if attempt > 0:
                        print(f"DEBUG: Download succeeded after {attempt + 1} attempts")
                    return True
                    
            except Exception as e:
                print(f"DEBUG: Download attempt {attempt + 1} failed: {e}")
                
            # Don't wait after the last attempt
            if attempt < max_retries - 1:
                # Exponential backoff: 2^attempt seconds (2, 4, 8...)
                delay = 2 ** attempt
                print(f"DEBUG: Retrying in {delay} seconds...")
                time.sleep(delay)
        
        print(f"DEBUG: All {max_retries} download attempts failed for {item_name}")
        return False

    def _download_manifest_file(self, section, item_name):
        """
        Download a specific file from the server using chunked download.
        
        Args:
            section (str): '_internal', 'data', 'temp', 'icons', or 'styles'
            item_name (str): Name of the item to download
        
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Map section to folder parameter
            if section == "_internal":
                folder = "internal"
            elif section == "data":
                folder = "data"
            elif section == "temp":
                folder = "temp"
            elif section == "icons":
                folder = "icons"
            elif section == "styles":
                folder = "styles"
            else:
                print(f"DEBUG: Unknown section '{section}'")
                return False
            
            # Construct download URL
            url = f"{self.base_url}/download_file"
            params = {
                'program': 'eintzofia',
                'content': item_name,
                'folder': folder
            }
            
            # Enable streaming for chunked download
            response = requests.get(url, params=params, stream=True, timeout=(10, 300))
            response.raise_for_status()
            
            # Get file size from headers
            total_size = int(response.headers.get("content-length") or 0)
            downloaded = 0
            next_report = 1024 * 1024  # 1MB
            
            # Determine save path based on section
            eintzofia_root = os.path.dirname(self.parent.settings['File_Path'])
            if section == "_internal":
                save_dir = os.path.join(eintzofia_root, '_internal')
            elif section == "data":
                save_dir = os.path.join(eintzofia_root, '_internal', 'data')
            elif section == "temp":
                save_dir = os.path.join(eintzofia_root, '_internal', 'temp')
            elif section == "icons":
                save_dir = os.path.join(eintzofia_root, '_internal', 'monitor', 'gui', 'icons')
            elif section == "styles":
                save_dir = os.path.join(eintzofia_root, '_internal', 'monitor', 'gui', 'styles')
            
            os.makedirs(save_dir, exist_ok=True)
            zip_path = os.path.join(save_dir, f"{item_name}.zip")
            
            print(f"DEBUG: Downloading {item_name} ({self._format_file_size(total_size)})")
            
            # Download to temporary file for atomic operation
            tmp_zip_path = zip_path + ".part"
            
            with open(tmp_zip_path, "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if not chunk:
                        continue
                    f.write(chunk)
                    downloaded += len(chunk)
                    
                    if downloaded >= next_report:
                        if total_size:
                            progress = downloaded / total_size * 100
                            print(f"DEBUG: {progress:.1f}% ({self._format_file_size(downloaded)}/{self._format_file_size(total_size)})")
                        else:
                            print(f"DEBUG: Downloaded {self._format_file_size(downloaded)}")
                        next_report += 1024 * 1024
            
            # Atomic file operation
            os.replace(tmp_zip_path, zip_path)
            
            print(f"DEBUG: Download completed: {item_name}")
            
            # Validate downloaded file
            if not zipfile.is_zipfile(zip_path):
                print("DEBUG: Downloaded file is not a zip")
                os.remove(zip_path)
                return False
            
            # Extract zip file
            with zipfile.ZipFile(zip_path, "r") as zip_ref:
                zip_ref.extractall(save_dir)
            
            # Clean up zip file
            os.remove(zip_path)
            
            return True
                
        except Exception as e:
            print(f"DEBUG: Exception in _download_manifest_file: {e}")
            return False

    def _format_file_size(self, size_bytes):
        """Format file size with appropriate units."""
        if size_bytes < 1024:
            return f"{size_bytes} B"
        elif size_bytes < 1024 * 1024:
            return f"{size_bytes / 1024:.1f} KB"  
        else:
            return f"{size_bytes / (1024 * 1024):.1f} MB"

    def download_monitor_downloader(self, save_path):
        """
        Download monitor downloader ZIP from server and extract the executable.
        
        Args:
            save_path: Full path where to save the downloader executable
            
        Returns:
            bool: True if download successful, False otherwise
        """
        url = f"{self.base_url}/download_monitor_downloader"
        
        try:
            print(f"DEBUG: Downloading monitor downloader ZIP from {url}")
            response = requests.get(url, stream=True, timeout=(30, 3600))  # Match monitor download timeout
            response.raise_for_status()
            
            total_size = int(response.headers.get("content-length") or 0)
            downloaded = 0
            
            print(f"DEBUG: Downloading monitor downloader ZIP ({self._format_file_size(total_size)})")
            
            # Create directory if needed
            os.makedirs(os.path.dirname(save_path), exist_ok=True)
            
            # Download to ZIP file first
            zip_path = save_path.replace('.exe', '.zip')  # Create zip filename
            
            with open(zip_path, "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if not chunk:
                        continue
                    f.write(chunk)
                    downloaded += len(chunk)
                    
                    if total_size and downloaded % (1024 * 1024) == 0:
                        progress = downloaded / total_size * 100
                        print(f"DEBUG: Download progress: {progress:.1f}% ({self._format_file_size(downloaded)}/{self._format_file_size(total_size)})")
            
            print(f"DEBUG: ZIP download completed: {zip_path}")
            
            # Validate it's a ZIP file
            if not zipfile.is_zipfile(zip_path):
                print(f"DEBUG: Downloaded file is not a valid ZIP archive")
                os.remove(zip_path)
                return False
            
            # Extract the ZIP file
            extract_dir = os.path.dirname(save_path)
            
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(extract_dir)
            
            print(f"DEBUG: Extracted ZIP contents to: {extract_dir}")
            
            # Find the executable in extracted files
            executable_name = "monitor_downloader.exe" if sys.platform.startswith("win") else "monitor_downloader"
            
            # Look for the executable
            found_executable = None
            for root, dirs, files in os.walk(extract_dir):
                for file in files:
                    if file.lower() == executable_name.lower():
                        found_executable = os.path.join(root, file)
                        break
                if found_executable:
                    break
            
            if not found_executable:
                print(f"DEBUG: Could not find {executable_name} in extracted files")
                os.remove(zip_path)
                return False
            
            # Move executable to final location if it's not already there
            if found_executable != save_path:
                if os.path.exists(save_path):
                    os.remove(save_path)
                os.rename(found_executable, save_path)
                print(f"DEBUG: Moved executable to: {save_path}")
            
            # Set executable permissions
            if sys.platform.startswith("win"):
                os.chmod(save_path, stat.S_IRUSR | stat.S_IWUSR | stat.S_IXUSR | 
                        stat.S_IRGRP | stat.S_IXGRP | stat.S_IROTH | stat.S_IXOTH)
            else:
                os.chmod(save_path, stat.S_IRWXU | stat.S_IRGRP | stat.S_IXGRP | stat.S_IROTH | stat.S_IXOTH)
            
            # Clean up ZIP file
            os.remove(zip_path)
            print(f"DEBUG: Cleaned up ZIP file")
            
            # Verify final executable
            if os.path.exists(save_path) and os.path.getsize(save_path) > 0:
                print(f"DEBUG: Monitor downloader successfully extracted: {save_path}")
                print(f"DEBUG: Final file size: {self._format_file_size(os.path.getsize(save_path))}")
                return True
            else:
                print(f"DEBUG: Final executable validation failed")
                return False
            
        except requests.exceptions.RequestException as e:
            print(f"DEBUG: Request error downloading monitor downloader: {e}")
            return False
        except zipfile.BadZipFile as e:
            print(f"DEBUG: Invalid ZIP file: {e}")
            if 'zip_path' in locals() and os.path.exists(zip_path):
                os.remove(zip_path)
            return False
        except Exception as e:
            print(f"DEBUG: Error downloading monitor downloader: {e}")
            if 'zip_path' in locals() and os.path.exists(zip_path):
                os.remove(zip_path)
            return False

if __name__ == '__main__':
    OS_manager = os_manager()
    server = ServerManager()
    #server.send_email_debug()
    server.set_download_files(locations=["Dan's PC"], eintzofia_download=True, monitor_download=True, model_download=False)

    