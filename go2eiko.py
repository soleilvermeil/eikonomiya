import requests
import os
import re
import logging
import argparse
from typing import Union
import glob
import shutil
import stat


# Constants
EXTENSIONS = ['png', 'jpg', 'jpeg']
AUTH = None  # TODO: might not be the most secured way to store the credentials
DEFAULT_MASTER_OUTPUT_PATH = "./data/"

# Informations about the repository
OWNER = "frzyc"
REPO = "genshin-optimizer"


# User specific
METHOD = None
MASTER_OUTPUT_PATH = DEFAULT_MASTER_OUTPUT_PATH
TEMP_FOLDER = os.path.join(MASTER_OUTPUT_PATH, "temp")
FORCE = None


def sparse_checkout(path_to_checkout: str):

    # Get current path
    current_path = os.getcwd()

    # Clone the repository
    temp_folder_path = os.path.join(current_path, TEMP_FOLDER)
    os.makedirs(temp_folder_path, exist_ok=True)
    os.chdir(temp_folder_path)
    os.system(f"git clone --filter=blob:none --no-checkout https://github.com/frzyc/genshin-optimizer.git")
    os.chdir("genshin-optimizer")
    os.system(f"git config core.sparseCheckout true")
    os.system(f"echo {path_to_checkout} >> .git/info/sparse-checkout")
    os.system("git checkout")
    os.system("git pull")

    # Go back to the original folder
    os.chdir(current_path)


def del_temp_folder():

    # Set all files to writeable
    files = glob.glob(os.path.join(TEMP_FOLDER, REPO, ".git", "**", "*"), recursive=True)
    for file in files:
        os.chmod(file, stat.S_IWRITE)

    # Delete the folder
    shutil.rmtree(TEMP_FOLDER, REPO)


def intex_dot_ts2name_converter(index_dot_ts: str, old_filename: str) -> str:
    
    # Convert the name using the index.ts file
    new_filename = old_filename.split(".")[0]
    ext = old_filename.split(".")[1]
    pattern = r"import ([A-Za-z0-9]+) from '.\/([A-Za-z0-9_]+)\.([a-z]+)'"
    for line in index_dot_ts.split("\n"):
        if re.match(pattern, line):
            new_filename = re.search(pattern, line).group(1)
            ext = re.search(pattern, line).group(3)
            if re.search(pattern, line).group(2) + "." + ext == old_filename:
                break

    # Convert the resulting name to match eikonomiya's convention
    d = {
        "constellation1": "c1",
        "constellation2": "c2",
        "constellation3": "c3",
        "constellation4": "c4",
        "constellation5": "c5",
        "constellation6": "c6",
        "icon": "face",
        "banner": "namecard",
        "skill": "skill",
        "burst": "burst",
        "passive1": "a1",
        "passive2": "a4",
    }
    return f"{d[new_filename]}.{ext}" if new_filename in d else old_filename


def download_folder(
    path: str,
    output_path: Union[str, callable],
    name_converter: callable,
):
    """
    Download all the files in a folder of a GitHub repository.
    
    Parameters
    ----------
    path : str
        Path of the folder in the repository. Usually it is right after
        "tree/master/" in the repository's URL.
    output_path : Union[str, callable]
        Path of the folder where the files will be saved. Can be a relative
        path or an absolute path. If a callable, it should take a single
        argument corresponding to the name of the file as stored in the
        repository, and return the path of the file as it should be saved.
    name_converter : callable
        The function that converts the name of the file. It should take a
        single argument corresponding to the name of the file as stored in the
        repository, and return the name of the file as it should be saved.
    """

    if METHOD == "checkout":

        # Getting all images of the checked out repo
        images = glob.glob(os.path.join(TEMP_FOLDER, REPO, path, "*"), recursive=False)
        logging.info(f"Found {len(images)} images in " + os.path.join(path, "*"))
        for image in images:
            ext = image.split(".")[-1]
            if ext not in EXTENSIONS:
                continue

            # Getting the new filename
            old_filename = os.path.basename(image)
            filename = name_converter(old_filename)

            # Getting the path for the current image
            real_output_path = None
            if callable(output_path):
                real_output_path = output_path(old_filename)
            else:
                real_output_path = output_path
            real_output_path = os.path.join(MASTER_OUTPUT_PATH, real_output_path)
            os.makedirs(real_output_path, exist_ok=True)

            # Copy the image to the output folder
            shutil.copy(image, os.path.join(real_output_path, filename))
            logging.info(f"Downloaded {filename}!")

        return

    # Getting all images of the set
    url = f"https://api.github.com/repos/{OWNER}/{REPO}/contents/{path}"
    response = requests.get(url, auth=AUTH)  # TODO: lower the number of requests
    if response.status_code == 200:
        contents = response.json()
        images = [
            file['download_url']
            for file in contents
            if file['type'] == 'file'
            and file['name'].lower().endswith(tuple(EXTENSIONS))
        ]

        # Downloading all the images
        for image in images:
            response = requests.get(image, auth=AUTH)  # TODO: lower the number of requests
            old_filename = image.split("/")[-1]
            filename = name_converter(old_filename)
            
            real_output_path = None
            if callable(output_path):
                real_output_path = output_path(old_filename)
            else:
                real_output_path = output_path
            
    
            # Create a local folder (if needed)
            logging.info(f"Trying to download {path}...")
            folder_path = os.path.join(MASTER_OUTPUT_PATH, real_output_path)
            os.makedirs(folder_path, exist_ok=True)
            
            # Save the file in the folder
            with open(os.path.join(MASTER_OUTPUT_PATH, real_output_path, filename), 'wb') as f:
                f.write(response.content)
            logging.info(f"Downloaded {filename}!")


def download_recursively(
    path: str,
    output_path: str,
    name_converter: Union[str, callable],
    force_download: bool = False,
    expected_files: int = 1,
):
    """
    Download all the files in a folder of a GitHub repository recursively. In
    fact, this function is NOT really recursive, but will only download the
    files in the first level of the given folder.

    Parameters
    ----------
    path : str
        Path of the folder in the repository. Usually it is right after
        "tree/master/" in the repository's URL.
    output_path : str
        Path of the folder where the files will be saved. Can be a relative
        path or an absolute path.
    name_converter : Union[str, callable]
        If a callable, it is the function that converts the name of the file.
        It should take a single argument corresponding to the name of the file
        as stored in the repository, and return the name of the file as it
        should be saved. If a string, it should be "index.ts", meaning that
        the function will try to use the index.ts file to convert the names. If
        the string is not "index.ts", the function will use the original name
        of the file.
    force_download : bool, optional
        If True, the function will download all the files again, even if they
        already exist in the output folder. If False, the function will skip
        folders which already have the expected number of files, by default
        False
    expected_files : int, optional
        When force_download is False, the function will skip folders which
        already have this number of files (or more), by default 1

    Notes
    -----
    When using the method "checkout", it will always ignore "force_download"
    and "expected_files", as it will download all the files in the given path.
    Since doing a checkout does not use the GitHub API, this method might be
    faster and can be used without rate limits.
    """

    if METHOD == "checkout":

        # Getting all images of the checked out repo
        images = glob.glob(os.path.join(TEMP_FOLDER, REPO, path, "**", "*"), recursive=True)
        logging.info(f"Found {len(images)} images in " + os.path.join(path, "**", "*"))
        for image in images:
            ext = image.split(".")[-1]
            if ext not in EXTENSIONS:
                continue

            # Getting the new filename
            old_filename = os.path.basename(image)
            if callable(name_converter):
                filename = name_converter(old_filename)
            elif isinstance(name_converter, str) and name_converter == "index.ts":
                image_folder = os.path.dirname(image)
                index_dot_ts = open(os.path.join(image_folder, "index.ts")).read()
                filename = intex_dot_ts2name_converter(index_dot_ts, old_filename)

            # Getting the path for the current image
            folder = os.path.basename(os.path.dirname(image))
            real_output_path = os.path.join(MASTER_OUTPUT_PATH, output_path, folder.lower())
            os.makedirs(real_output_path, exist_ok=True)

            # Copy the image to the output folder
            shutil.copy(image, os.path.join(real_output_path, filename))
            logging.info(f"Downloaded {filename}!")

        return

    # Getting all folders
    url = f"https://api.github.com/repos/{OWNER}/{REPO}/contents/{path}"
    response = requests.get(url, auth=AUTH)  # TODO: lower the number of requests

    # Check if there is a field "message"
    if "message" in response.json():
        logging.error(f"Error: {response.json()['message']}")
        return
    
    if response.status_code == 200:
        contents = response.json()
        folders = [file['name'] for file in contents if file['type'] == 'dir']
        for folder in folders:

            # DEBUG
            # if folder != "Furina":
            #     continue

            # Create a local folder for each folder in the repo
            logging.info(f"Trying to download {folder}...")
            folder_path = os.path.join(MASTER_OUTPUT_PATH, output_path, folder.lower())
            os.makedirs(folder_path, exist_ok=True)

            # Check if the folder already exists
            if not force_download and len(os.listdir(folder_path)) >= expected_files:
                logging.info(f"Skipping as it already exists!")
                continue

            # Getting all images of the set
            url = f"https://api.github.com/repos/{OWNER}/{REPO}/contents/{path}/{folder}"
            response = requests.get(url, auth=AUTH)  # TODO: lower the number of requests
            if response.status_code == 200:
                contents = response.json()
                images = [
                    file['download_url']
                    for file in contents
                    if file['type'] == 'file'
                    and file['name'].lower().endswith(tuple(EXTENSIONS))
                ]
                if isinstance(name_converter, str) and name_converter == "index.ts":
                    index_dot_ts = requests.get(f"https://raw.githubusercontent.com/{OWNER}/{REPO}/master/{path}/{folder}/index.ts").text

                # Downloading all the images
                for image in images:
                    response = requests.get(image, auth=AUTH)  # TODO: lower the number of requests
                    old_filename = image.split("/")[-1]
                    if callable(name_converter):
                        filename = name_converter(old_filename)
                    elif isinstance(name_converter, str) and name_converter == "index.ts":
                        filename = intex_dot_ts2name_converter(index_dot_ts, old_filename)
                    with open(os.path.join(MASTER_OUTPUT_PATH, output_path, folder.lower(), filename), 'wb') as f:
                        f.write(response.content)
                    logging.info(f"Downloaded {filename}!")


def download_artifacts():

    # Defining how to extract the names of the files
    def name_converter(old_filename: str) -> str:

        # Define the pattern
        pattern = r"UI_RelicIcon_\d+_(\d)\.([a-z]+)"

        # Get extension
        ext = re.search(pattern, old_filename).group(2)

        # Get the filename
        number2artifact = {
            "1": "coupe",
            "2": "plume",
            "3": "couronne",
            "4": "fleur",
            "5": "sablier",
        }
        filename = number2artifact[re.search(pattern, old_filename).group(1)]
        return f"{filename}.{ext}"

    # Downloading the artifacts
    download_recursively(
        path="libs/gi/assets/src/gen/artifacts",
        output_path="gamedata/assets/artifacts/",
        name_converter=name_converter,
        force_download=FORCE,
        expected_files=5,
    )


def download_characters():
    
    # Character's base assets
    download_recursively(
        path = "libs/gi/assets/src/gen/chars",
        output_path="gamedata/assets/characters/",
        name_converter="index.ts",
        force_download=FORCE,
        expected_files=15,
    )
    
    # Character namecards
    def name_converter(old_filename: str) -> str:
        ext = old_filename.split(".")[-1]
        return f"card.{ext}"
    
    def output_path(old_filename: str) -> str:
        if "Character" in old_filename:
            pattern = "Character_([A-Za-z_]+)_Card\.[a-z]+"
            character_name = re.search(pattern, old_filename).group(1).lower()
        elif "Traveler" in old_filename:
            if "Traveler_Female" in old_filename:
                character_name = "travelerf"
            elif "Traveler_M" in old_filename:
                character_name = "travelerm"
        while "_" in character_name:
            character_name = character_name.replace("_", "")
        return os.path.join("gamedata/assets/characters", character_name)
    
    download_folder(
        path="libs/gi/char-cards/src",
        output_path=output_path,
        name_converter=name_converter,
    )


def download_weapons():

    def name_converter(old_filename: str) -> str:
        
        # Get the extension
        ext = old_filename.split(".")[-1]

        # Check in which case we are
        if "Awaken" in old_filename:
            return f"weapon-awake.{ext}"
        else:
            return f"weapon.{ext}"
    
    download_recursively(
        path = "libs/gi/assets/src/gen/weapons",
        output_path="gamedata/assets/weapons/",
        name_converter=name_converter,
        force_download=FORCE,
        expected_files=15,
    )


def main(**kwargs):

    os.makedirs(MASTER_OUTPUT_PATH, exist_ok=True)

    if METHOD == "checkout":
        sparse_checkout(path_to_checkout="libs/gi/assets/src/gen")
        sparse_checkout(path_to_checkout="libs/gi/char-cards/src")

    if kwargs["characters"]:
        download_characters()

    if kwargs["artifacts"]:
        download_artifacts()
    
    if kwargs["weapons"]:
        download_weapons()

    if METHOD == "checkout" and not kwargs["keep"]:
       del_temp_folder()


if __name__ == "__main__":

    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format="[%(asctime)s] [%(levelname)-8s] --- %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Setting up the parser
    parser = argparse.ArgumentParser(
        description="Download the assets from Genshin Optimizer"
    )
    parser.add_argument("--method", "-m", type=str, help="Method to use", choices=["api", "checkout"], required=True)
    parser.add_argument("--characters", "-c", action="store_true", help="Download the characters' assets")
    parser.add_argument("--weapons", "-w", action="store_true", help="Download the weapons' assets")
    parser.add_argument("--artifacts", "-a", action="store_true", help="Download the artifacts' assets")
    parser.add_argument("--force", "-f", action="store_true", help="Force the redownload of all the assets")
    parser.add_argument("--output", "-o", type=str, help="Path of the 'data' folder", default=DEFAULT_MASTER_OUTPUT_PATH)
    parser.add_argument("--keep", "-k", action="store_true", help="If using 'checkout' method, keep the temp folder")
    kwargs = vars(parser.parse_args())
    MASTER_OUTPUT_PATH = kwargs["output"]
    TEMP_FOLDER = os.path.join(MASTER_OUTPUT_PATH, "temp")
    FORCE = kwargs["force"]
    METHOD = kwargs["method"]

    # Logging to GitHub's API
    if METHOD == "api":
        env_vars = [
            "EIKONOMIYA_GITHUB_USERNAME",
            "EIKONOMIYA_GITHUB_TOKEN",
        ]
        if not all(env_var in os.environ for env_var in env_vars):
            logging.error("Please define the following environment variables: " + ", ".join(env_vars) + ".")
            exit(1)
        username = os.environ[env_vars[0]]
        token = os.environ[env_vars[1]]
        AUTH = (username, token)

    # Run the main function
    main(**kwargs)
