#!/usr/bin/env python3
import os

INSTALL_DIR = os.path.join(os.path.sep, 'opt', 'cromwell')
JAR_DIR = os.path.join(INSTALL_DIR, "jar")
CONFIG_DIR = os.path.join(INSTALL_DIR, "config")
SHARED_DIR = os.path.join(os.path.sep, 'shared')

GOOGLE_URL = "http://metadata.google.internal/computeMetadata/v1/instance/attributes"
CROMWELL_DOWNLOAD = "https://github.com/broadinstitute/cromwell/releases/download"


def create_directories():
    print("Create directories...")
    for dn in (INSTALL_DIR, JAR_DIR, CONFIG_DIR, SHARED_DIR):
        if not os.path.exists(dn):
            os.makedirs(dn)
    os.system(f'chmod -R 777 {SHARED_DIR}')
    print("Create directories... DONE")


def install_packages():
    print("Install packages...")
    packages = [
        'curl',
        'default-jdk', 'git',
        'less',
        'emacs', 'vim',
        'python3-pip',
        'python3-dev',
        'python3-setuptools'
    ]

    os.system('apt-get update')
    os.system('apt-get install -y ' + ' '.join(packages))
    # Python deps
    os.system('python3 -m pip install requests>=2.20.0')

    print("Install packages... DONE")


def install_cromwell():
    print("Install cromwell...")
    import requests
    jar_path = os.path.join(JAR_DIR, "cromwell.jar")
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
    download_from_metadata('cromwell-conf', os.path.join(CONFIG_DIR, 'cromwell.conf'))
    download_from_metadata('helpers-sh', os.path.join(SHARED_DIR, 'helpers.sh'))
    clone_analysis_wdls()
    print("Startup script...DONE")
