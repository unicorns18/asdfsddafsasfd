# Google Drive API

CREDENTIALS = 'credentials/credentials.json'

import sys
import google_auth_oauthlib
from googleapiclient.errors import HttpError
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.http import MediaFileUpload
import os
import pickle
from googleapiclient.http import MediaIoBaseDownload

class Drive:
    def __init__(self):
        self.SCOPES = ['https://www.googleapis.com/auth/drive']
        self.creds = self._load_credentials()
        if self.creds:
            self.service = build('drive', 'v3', credentials=self.creds)
        else:
            print('Failed to initialize Drive service.')
            sys.exit(1)
        
    def _load_credentials(self):
        creds = None
        if os.path.exists('token.pickle'):
            print('Loading credentials from token.pickle')
            try:
                with open('token.pickle', 'rb') as token:
                    creds = pickle.load(token)
            except (IOError, pickle.UnpicklingError) as exc:
                print(f"Error loading credentials: {str(exc)}")
                os.remove('token.pickle')                    
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                print('Refreshing token')
                try:
                    creds.refresh(Request())
                except google_auth_oauthlib.auth.exceptions.RefreshError as refresh_exc:
                    print(f"Error refreshing credentials: {str(refresh_exc)}")
                    if "Token has been expired or revoked" in str(refresh_exc):
                        os.remove('token.pickle')
                        print('Token removed')
                    else:
                        raise
                except Exception as e:
                    print(f"Unexpected error while refreshing credentials: {str(e)}")
                    raise
            else:
                print('Fetching new token')
                try:
                    flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS, self.SCOPES)
                    creds = flow.run_local_server(port=0)
                except FileNotFoundError as file_not_found_exc:
                    print(f"Client secrets file {CREDENTIALS} not found.")
                    return None
                except Exception as e:
                    print(f"Unexpected error while fetching new token: {str(e)}")
                    raise
            try:
                with open('token.pickle', 'wb') as token:
                    print('Saving credentials to token.pickle')
                    pickle.dump(creds, token)
            except IOError as io_exc:
                print(f"Error saving credentials to token.pickle: {str(io_exc)}")
        return creds
        
    def upload_file(self, file_path, folder_id):
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File {file_path} not found")
        
        file_name = os.path.basename(file_path)
        file_metadata = {
            'name': file_name,
            'parents': [folder_id]
        }
        
        try:
            media = MediaFileUpload(file_path, resumable=True)
            file = self.service.files().create(body=file_metadata, media_body=media, fields='id').execute()
            file_id = file.get('id')
            if not file_id:
                raise Exception(f"Failed to upload file {file_name}")
            permission = {
                'type': 'anyone',
                'role': 'reader'
            }
            self.service.permissions().create(fileId=file_id, body=permission).execute()
            return file_id
        except HttpError as httpexc:
            print(f'An error occurred: {httpexc}')
            return None
    
    def create_folder(self, folder_name):
        """
        Creates a new folder with the given name and returns its ID.
        The folder is created with 'anyone' role set to 'reader'.
        """
        file_metadata = {
            'name': folder_name,
            'mimeType': 'application/vnd.google-apps.folder'
        }
        try:
            file = self.service.files().create(body=file_metadata, fields='id').execute()
            folder_id = file.get('id')
            if not folder_id:
                raise Exception(f"Failed to create folder '{folder_name}'")
            permission = {
                'type': 'anyone',
                'role': 'reader'
            }
            self.service.permissions().create(fileId=folder_id, body=permission).execute()
            print(f"Folder '{folder_name}' created with ID: {folder_id}")
            return folder_id
        except HttpError as e:
            raise Exception(f"Error creating folder '{folder_name}': {e}")
    
    def clean_user_id(self, user_id):
        cleaned_user_id = user_id.strip("`")
        return str(cleaned_user_id)
    
    def list_files(self, folder_id, images_only: bool = False):
        """
        Lists files in the given folder ID.
        If images_only is True, only files with MIME type containing 'image/' are returned.
        Returns a list of dictionaries containing file metadata.
        """
        try:
            folder_id = self.clean_user_id(folder_id)
            query = f"'{folder_id}' in parents"
            if images_only:
                query += " and mimeType contains 'image/'"
            results = self.service.files().list(q=query, fields='files(id, name, mimeType, modifiedTime, size)').execute()
            return results.get('files', [])
        except HttpError as e:
            raise Exception(f"Error listing files in folder '{folder_id}': {e}")
    
    def download_file(self, file_id, file_path):
        """
        Downloads the file with the given file_id to the specified file_path.
        """
        try:
            request = self.service.files().get_media(fileId=file_id)
            with open(file_path, 'wb') as fh:
                downloader = MediaIoBaseDownload(fh, request)
                done = False
                while not done:
                    status, done = downloader.next_chunk()
                    print(f'Download progress: {int(status.progress() * 100)}%')
        except HttpError as e:
            if e.resp.status == 404:
                raise FileNotFoundError(f"File with ID '{file_id}' not found.")
            else:
                raise Exception(f"Error downloading file '{file_id}': {e}")
        except FileExistsError:
            raise FileExistsError(f"File '{file_path}' already exists. Please choose a different path.")

    def delete_file(self, file_id):
        self.service.files().delete(fileId=file_id).execute()
        print(f'File ID: {file_id} deleted')
        
    def delete_folder(self, folder_id):
        self.service.files().delete(fileId=folder_id).execute()
        print(f'Folder ID: {folder_id} deleted')
        
    def get_folder_id(self, folder_name):
        results = self.service.files().list(q=f"name='{folder_name}' and mimeType='application/vnd.google-apps.folder'", fields='files(id)').execute()
        items = results.get('files', [])
        if not items:
            return None
        return items[0].get('id')
    
    def get_file_id(self, file_name, folder_id):
        results = self.service.files().list(q=f"name='{file_name}' and '{folder_id}' in parents", fields='files(id)').execute()
        items = results.get('files', [])
        if not items:
            return None
        return items[0].get('id')
    
    def get_file_link(self, file_id):
        return f'https://drive.google.com/file/d/{file_id}/view'
    
    def get_folder_link(self, folder_id):
        return f'https://drive.google.com/drive/folders/{folder_id}'
    
    def get_file_info(self, file_id):
        return self.service.files().get(fileId=file_id, fields='id, name, mimeType, modifiedTime, size').execute()
    
    def update_folder_names(self):
        items = self.list_files('root')
        for item in items:
            if item['mimeType'] == 'application/vnd.google-apps.folder' and item['name'] != "Weirdos":
                new_name = f"blacklist-{item['name']}"
                file_metadata = {'name': new_name}
                self.service.files().update(fileId=item['id'], body=file_metadata).execute()
                print(f'Folder ID: {item["id"]} updated to {new_name}')
                
    def retrieve_folder_ids(self):
        folders_list = []
        items = self.list_files('root')
        for item in items:
            if item['mimeType'] == 'application/vnd.google-apps.folder':
                if item['name'] != "Weirdos":
                    folders_list.append((item['name'], item['id']))
        with open('folders_list.txt', 'w') as file:
            for name, folder_id in folders_list:
                file.write(f'{name} {folder_id}\n')
        print('Folder names and IDs written to folders_list.txt')
        
    def set_all_folders_to_everyone(self):
        items = self.list_files('root')
        for item in items:
            if item['mimeType'] == 'application/vnd.google-apps.folder':
                permission = {
                    'type': 'anyone',
                    'role': 'reader'
                }
                self.service.permissions().create(fileId=item['id'], body=permission).execute()
                print(f'Folder ID: {item["id"]} set to everyone')
    
    def get_direct_image_url(self, file_id):
        """
        Gets the direct URL for an image file that can be used in <img> tags.
        
        Args:
            file_id (str): The ID of the file in Google Drive
            
        Returns:
            str: Direct URL for the image
        """
        try:
            file_info = self.get_file_info(file_id)
            if not file_info['mimeType'].startswith('image/'):
                raise ValueError(f"File with ID '{file_id}' is not an image")
            return f'https://drive.usercontent.google.com/download?id={file_id}&export=view&authuser=0'
        except HttpError as e:
            if e.resp.status == 404:
                raise FileNotFoundError(f"File with ID '{file_id}' not found")
            else:
                raise Exception(f"Error getting direct URL for file '{file_id}': {e}")
    
    def download_folder_images(self, folder_id, base_path="/root/blacklistimages"):
        try:
            folder_info = self.service.files().get(fileId=folder_id, fields='name').execute()
            folder_name = folder_info['name']
            folder_path = os.path.join(base_path, folder_name)
            os.makedirs(folder_path, exist_ok=True)
            image_files = self.list_files(folder_id, images_only=True)
            print(f"Downloading {len(image_files)} images from folder '{folder_name}'...")
            for image in image_files:
                file_path = os.path.join(folder_path, image['name'])
                print(f"Downloading {image['name']}...")
                self.download_file(image['id'], file_path)
            print(f"Successfully downloaded all images to {folder_path}")
            return folder_path
        except Exception as e:
            print(f"Error downloading folder: {str(e)}")
            return None
    
    def list_folders(self):
        results = self.service.files().list(q="mimeType='application/vnd.google-apps.folder'", fields='files(id, name)').execute()
        return results.get('files', [])
    
    def download_all_blacklist_folders(self, base_path="/root/blacklistimages"):
        try:
            folders = self.list_folders()
            blacklist_folders = [folder for folder in folders if folder['name'].startswith('blacklist-')]
            print(f"Found {len(blacklist_folders)} blacklist folders")
            for folder in blacklist_folders:
                print(f"\nProcessing folder: {folder['name']}")
                self.download_folder_images(folder['id'], base_path)
            print("\nCompleted downloading all blacklist folders")
        except Exception as e:
            print(f"Error in download_all_blacklist_folders: {str(e)}")


if __name__ == '__main__':
    drive = Drive()
    