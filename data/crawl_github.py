import os
import requests
import zipfile
import io
from time import sleep
from configs.env import settings

GITHUB_TOKEN = settings.GITHUB_TOKEN
SEARCH_QUERY = "fastapi agents llms language:python" 
MAX_REPOS = 10
OUTPUT_DIR = "data/raw/git_repos"

HEADERS = {
    "Authorization": f"token {GITHUB_TOKEN}",
    "Accept": "application/vnd.github.v3+json"
}

def search_repositories(query, max_results=50):
    print(f"Searching repos with query: '{query}'...")   
    repos = []
    page = 1
    
    while len(repos) < max_results:
        url = f"https://api.github.com/search/repositories?q={query}&sort=stars&order=desc&per_page=100&page={page}"
        response = requests.get(url, headers=HEADERS)
        
        if response.status_code != 200:
            print(f"Error API: {response.json().get('message')}")
            break
            
        data = response.json()
        items = data.get("items", [])
        
        if not items:
            break
            
        for item in items:
            repos.append({
                "name": item["name"],
                "full_name": item["full_name"],
                "default_branch": item["default_branch"],
                "stars": item["stargazers_count"]
            })
            if len(repos) >= max_results:
                break
        page += 1
        sleep(1)

    return repos

def download_and_extract_repo(repo_info, output_dir):
    full_name = repo_info['full_name']
    branch = repo_info['default_branch']
    
    zip_url = f"https://api.github.com/repos/{full_name}/zipball/{branch}"
    print(f"Downloading {full_name} ({repo_info['stars']} stars)...")
    
    response = requests.get(zip_url, headers=HEADERS)
    if response.status_code != 200:
        print(f"  -> Cannot download: {full_name}")
        return

    try:
        with zipfile.ZipFile(io.BytesIO(response.content)) as z:
            py_files = [f for f in z.namelist() if f.endswith('.py')]
            
            repo_folder_name = full_name.replace("/", "_")
            repo_out_path = os.path.join(output_dir, repo_folder_name)
            os.makedirs(repo_out_path, exist_ok=True)
            
            for file_path in py_files:
                if "test" in file_path.lower():
                    continue
                    
                filename = os.path.basename(file_path)
                if not filename:
                    continue
                    
                source = z.read(file_path)
                with open(os.path.join(repo_out_path, filename), "wb") as f:
                    f.write(source)
                    
    except zipfile.BadZipFile:
        print(f"Zip file error: {full_name}")

if __name__ == "__main__":
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    target_repos = search_repositories(SEARCH_QUERY, MAX_REPOS)
    print(f"Found {len(target_repos)} repositories.\n")
    
    for repo in target_repos:
        download_and_extract_repo(repo, OUTPUT_DIR)
        sleep(2)        
    print("\nDone")
