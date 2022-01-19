#!/usr/bin/env python3
import os

SHARED_DIR = os.path.join(os.path.sep, 'shared')

GOOGLE_URL = "http://metadata.google.internal/computeMetadata/v1/instance/attributes"
CROMWELL_DOWNLOAD = "https://github.com/broadinstitute/cromwell/releases/download"

PACKAGES = [
    # required to run
    'curl',
    'default-jdk',
    'git',
    'python3-pip',
    # just useful
    'less',
    'emacs', 'vim',
    'python3-dev',
    'python3-setuptools'
]


def create_directories():
    print("Create directories...")
    os.system(f'mkdir -p {SHARED_DIR}/cromwell')
    os.system(f'chmod -R 777 {SHARED_DIR}')
    print("Create directories... DONE")


def install_packages():
    print("Install packages...")
    os.system('apt-get update')
    os.system('apt-get install -y ' + ' '.join(PACKAGES))
    # Python deps
    os.system('python3 -m pip install requests>=2.20.0')

    print("Install packages... DONE")


def install_cromwell():
    print("Install cromwell...")
    import requests
    jar_path = os.path.join(SHARED_DIR, "cromwell", "cromwell.jar")
    if os.path.exists(jar_path):
        print("Already installed at {} ...".format(jar_path))
    else:
        version = _fetch_instance_info('cromwell-version')
        print(f"Installing cromwell version {version} at {jar_path} ...")
        url = f"https://github.com/broadinstitute/cromwell/releases/download/{version}/cromwell-{version}.jar"
        response = requests.get(url)
        if not response.ok:
            raise Exception("GET failed for {}".format(url))
        with open(jar_path, "wb") as f:
            f.write(response.content)
        print(f"Installed cromwell version {version} at {jar_path}")

    print("Install cromwell...DONE")


def start_cromwell_service():
    download_from_metadata('cromwell-service', os.path.join(os.path.sep, 'etc', 'systemd', 'system', 'cromwell.service'))
    os.system('systemctl daemon-reload')
    os.system('systemctl start cromwell')


def download_from_metadata(tag, dest_path):
    print(f"Download {tag}...")
    with open(dest_path, 'w') as f:
        f.write(_fetch_instance_info(tag))
    print(f"Download {tag}...DONE")


def clone_analysis_wdls():
    print(f"Clone griffithlab/analysis-wdls to {SHARED_DIR} ...")
    old_dir = os.getcwd()
    os.chdir(SHARED_DIR)
    status_code = os.system('git clone https://github.com/griffithlab/analysis-wdls.git')
    os.chdir(old_dir)
    if status_code != 0:
        raise Exception("Clone failed for griffithlab/analysis-wdls")
    print(f"Clone griffithlab/analysis-wdls to {SHARED_DIR} ...DONE")


def _fetch_instance_info(name):
    import requests
    url = "/".join([GOOGLE_URL, name])
    response = requests.get(url, headers={'Metadata-Flavor': 'Google'})
    if not response.ok:
        raise Exception("GET failed for {}".format(url))
    return response.text


if __name__ == '__main__':
    create_directories()
    install_packages()
    install_cromwell()
    download_from_metadata('helpers-sh', os.path.join(SHARED_DIR, 'helpers.sh'))
    download_from_metadata('cromwell-conf', os.path.join(SHARED_DIR, 'cromwell', 'cromwell.conf'))
    start_cromwell_service()
    clone_analysis_wdls()
    print("Startup script...DONE")
