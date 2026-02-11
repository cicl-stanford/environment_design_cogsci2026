import os
import re
import io
import requests
import pandas as pd

class OSFDataHandler:
    def __init__(self, node_id, filename_pattern=None):
        self.dataframes = []
        self.node_id = node_id
        self.ACCESS_TOKEN = os.environ.get('OSF_ID')
        self.filename_pattern = filename_pattern

    def add_dataframe(self, dataframe, metadata):
        self.dataframes.append({'dataframe': dataframe, 'metadata': metadata})

    def find(self, criteria=None):
        results = [item['dataframe'] for item in self.dataframes if all(item['metadata'].get(k) == v for k, v in criteria.items())]
        print(f'Found {len(results)} files matching specified criteria.')
        return results

    def extract_metadata(self, filename):
        pattern = r'(?P<project>[^-]+)-(?P<experiment>[^-]+)-(?P<iteration_name>[^-]+)-(?P<gameID>[a-f0-9\-]+)\.csv' if not self.filename_pattern else self.filename_pattern
        match = re.match(pattern, filename)
        if match:
            return match.groupdict()
        raise ValueError(f"Filename {filename} does not match the expected pattern.")

    def download_csv_file(self, file_url):
        headers = {
            'Authorization': f'Bearer {self.ACCESS_TOKEN}'
        }
        response = requests.get(file_url, headers=headers, allow_redirects=False)
        response.raise_for_status()
        
        if 'Location' in response.headers:
            redirect_url = response.headers['Location']
            response = requests.get(redirect_url, headers=headers)
            response.raise_for_status()
        
        return response.content.decode('utf-8')

    def fetch_node_files(self, provider='osfstorage'):
        url = f'https://api.osf.io/v2/nodes/{self.node_id}/files/{provider}/?sort=date_modified&page[size]=100'
        headers = {"Cache-Control": "no-cache"}
        if self.ACCESS_TOKEN:
            headers['Authorization'] = f'Bearer {self.ACCESS_TOKEN}'
            
        files = []
        while url:
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            data = response.json()
            files.extend(data['data'])
            url = data['links'].get('next')
        return files

    def get_project_name(self):
        url = f'https://api.osf.io/v2/nodes/{self.node_id}/'
        headers = {
            'Authorization': f'Bearer {self.ACCESS_TOKEN}'
        }
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        node_data = response.json()
        return node_data['data']['attributes']['title']

    def filter_files(self, criteria):
        files_info = self.fetch_node_files()
        filtered_files = []
        for file in files_info:
            filename = file['attributes']['name']
            if not filename.endswith('.csv'):
                continue

            try:
                metadata = self.extract_metadata(filename)
            except ValueError:
                print(f"Skipping file {filename} because it doesn't match the expected schema.")
                continue

            if all(metadata.get(k) == v for k, v in criteria.items()):
                filtered_files.append(file)                
        return filtered_files

    def load_filtered_csvs(self, criteria):
        filtered_files = self.filter_files(criteria)
        project_name = self.get_project_name()
        
        for file in filtered_files:
            filename = file['attributes']['name']
            file_url = file['links']['download']
            csv_content = self.download_csv_file(file_url)
            df = pd.read_csv(io.StringIO(csv_content))
            metadata = self.extract_metadata(filename)
            self.add_dataframe(df, metadata)
        print(f"Loaded {len(self.dataframes)} CSV files from project '{project_name}' (OSF node {self.node_id}).")
        return pd.concat([item['dataframe'] for item in self.dataframes]).reset_index(drop=True)