#!/usr/bin/env python3
import os

SHARED_DIR = os.path.join(os.path.sep, 'shared')

GOOGLE_URL = "http://metadata.google.internal/computeMetadata/v1/instance/attributes"
CROMWELL_DOWNLOAD = "https://github.com/broadinstitute/cromwell/releases/download"

PACKAGES = [
    # required to run
    'curl',
    'screen',
    'default-jdk',
    'git',
    'python3-pip',
    # just useful
    'zip',
    'less',
    'emacs', 'vim',
    'python3-dev',
    'python3-setuptools'
]


# Using a decorator to reduce logging annoyances
# Referenced this guide for construction:
# https://www.thecodeship.com/patterns/guide-to-python-function-decorators/
def bookends(func):
    """
    Print the `func`'s name and args at start and completion of function.
    e.g. `def install_packages()` with `@bookends` decorator will output the following

    install_packages...
    <stdout+stderr of the os.system calls>
    install_packages...DONE
    """
    def wrapper(*args, **kwargs):
        print(f"{func.__name__}...")
        result = func(*args, **kwargs)
        print(f"{func.__name__}...DONE")
        return result
    return wrapper


@bookends
def create_directories():
    os.system(f'mkdir -p {SHARED_DIR}/cromwell')
    os.system(f'chmod -R 777 {SHARED_DIR}')


@bookends
def install_packages():
    os.system('apt-get update')
    os.system('apt-get install -y ' + ' '.join(PACKAGES))
    # Python deps
    os.system('python3 -m pip install requests>=2.20.0')


@bookends
def install_cromwell():
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


def start_cromwell_service():
    download_from_metadata('cromwell-service', os.path.join(os.path.sep, 'etc', 'systemd', 'system', 'cromwell.service'))
    os.system('systemctl daemon-reload')
    os.system('systemctl start cromwell')


@bookends
def download_from_metadata(tag, dest_path):
    with open(dest_path, 'w') as f:
        f.write(_fetch_instance_info(tag))


@bookends
def clone_analysis_wdls():
    old_dir = os.getcwd()
    os.chdir(SHARED_DIR)
    status_code = os.system('git clone https://github.com/griffithlab/analysis-wdls.git')
    os.chdir(old_dir)
    if status_code != 0:
        raise Exception("Clone failed for griffithlab/analysis-wdls")
    os.system(f"bash {SHARED_DIR}/analysis-wdls/zip_wdls.sh")


def _fetch_instance_info(name):
    import requests
    url = "/".join([GOOGLE_URL, name])
    response = requests.get(url, headers={'Metadata-Flavor': 'Google'})
    if not response.ok:
        raise Exception("GET failed for {}".format(url))
    return response.text


@bookends
def startup_script():
    create_directories()
    install_packages()
    install_cromwell()
    download_from_metadata('helpers-sh', os.path.join(SHARED_DIR, 'helpers.sh'))
    download_from_metadata('cromwell-conf', os.path.join(SHARED_DIR, 'cromwell', 'cromwell.conf'))
    download_from_metadata('workflow-options', os.path.join(SHARED_DIR, 'cromwell', 'workflow_options.json'))
    download_from_metadata('persist-artifacts', os.path.join(SHARED_DIR, 'persist_artifacts.py'))
    download_from_metadata('pull-monitor-logs-sh', ps.path.join(SHARED_DIR, 'pull_monitor_logs.sh'))
    start_cromwell_service()
    clone_analysis_wdls()


if __name__ == '__main__':
    startup_script()
