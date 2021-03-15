#!/usr/bin/python3
import os, subprocess, sys

# Cromwell constants
CROMWELL_REPO = 'https://github.com/broadinstitute/cromwell'
CROMWELL_VERSION = 58

# name of .conf file for Cromwell on the VM instance. used in `cromwell.service`
CROMWELL_CONF = 'cromwell.conf'
# compute instance metadata tag with cromwell.conf contents. specified in `main.tf`
DOT_CONF_TAG='conf-file'
# compute instance metadata tag with cromwell.service contents. specified in `main.tf`
DOT_SERVICE_TAG='service-file'

GOOGLE_URL = "http://metadata.google.internal/computeMetadata/v1/instance/attributes"

# VM local directories
INSTALL_DIR = os.path.join(os.path.sep, 'opt', 'cromwell')
BIN_DIR = os.path.join(INSTALL_DIR, "bin")
JAR_DIR = os.path.join(INSTALL_DIR, "jar")
CONFIG_DIR = os.path.join(INSTALL_DIR, "config")


def create_directories():
    print("Create directories...")
    if not os.path.exists(INSTALL_DIR): os.makedirs(INSTALL_DIR)
    if not os.path.exists(BIN_DIR): os.makedirs(BIN_DIR)
    if not os.path.exists(JAR_DIR): os.makedirs(JAR_DIR)
    if not os.path.exists(CONFIG_DIR): os.makedirs(CONFIG_DIR)


def install_apt_get_packages():
    packages = [ 'python3-pip' 'default-jre' ]
    while subprocess.call(['apt-get', 'update']):
        print("Failed to apt-get update. Trying again in 5 seconds")
        time.sleep(5)
    while subprocess.call(['apt-get', 'install', '-y'] + packages):
        print("Failed to install packages with apt-get install. Trying again in 5 seconds")
        time.sleep(5)


def install_pip_packages():
    import pip._internal
    pip._internal.main(["install", "requests>=2.20.0"])


def install_packages():
    print("Install pacakges...")
    install_apt_get_packages()
    install_pip_packages()
    print("Install packages...DONE")


def install_broad_tool(name):
    """Install a .jar tool from the Broad Institute Cromwell repo."""
    import requests
    print("Install {} version {} ...".format(name, CROMWELL_VERSION))
    jar_fn = os.path.join(JAR_DIR, ".".join([name, "jar"]))
    if os.path.exists(jar_fn):
        print("Already installed at {} ...".format(jar_fn))
        return
    # fetch tool
    url = "{0}/releases/download/{1}/{2}-{1}.jar".format(
        CROMWELL_REPO, CROMWELL_VERSION, name
    )
    print("URL {}".format(url))
    response = requests.get(url)
    if not response.ok: raise Exception("GET failed for {}".format(url))
    # write tool to jar_fn
    print("Writing content to {}".format(jar_fn))
    with open(jar_fn, "wb") as f:
        f.write(response.content)


def install_cromwell():
    """Download cromwell and womtool to JAR_DIR."""
    print("Install cromwell and womtool...")
    os.chdir(JAR_DIR)
    for name in "cromwell", "womtool":
        install_broad_tool(name)

    print("Install cromwell...DONE")


def add_cromwell_profile():
    """Add BIN_DIR to PATH in /etc/profile.d/cromwell.sh"""
    fn = os.path.join(os.path.sep, 'etc', 'profile.d', 'cromwell.sh')
    print("Installing cromwell profile.d script to {}".format(fn))
    if os.path.exists(fn):
        print("Already installed cromwell profile.d config...SKIPPING")
    else:
        with open(fn, "w") as f:
            f.write('PATH={}:"${{PATH}}"'.format(BIN_DIR) + "\n")


def fetch_instance_info(name):
    """Pull data about booting instance from Google."""
    import requests
    url = "/".join([GOOGLE_URL, name])
    response = requests.get(url, headers={'Metadata-Flavor': 'Google'})
    if not response.ok:
        raise Exception("GET failed for {}".format(url))
    else:
        return response.text


# --- Cromwell systemctl service. Enables following logs with journalctl.

def fetch_and_save_instance_info(name, fn):
    """Store data about booting instance to file `fn`."""
    if os.path.exists(fn):
        print("Already installed {} to {} ... SKIPPING".format(name, fn))
    else:
        print("Install {} ...".format(fn))
        content = fetch_instance_info(name)
        with open(fn, 'w') as f:
            f.write(content)


def add_and_start_cromwell_service():
    """Create .service file and start service daemon for Cromwell."""
    fetch_and_save_instance_info(
        name=DOT_SERVICE_TAG,
        fn=os.path.join(os.path.sep, 'etc', 'systemd', 'system', 'cromwell.service')
    )
    print("Start cromwell service...")
    subprocess.check_call(['systemctl', 'daemon-reload'])
    subprocess.check_call(['systemctl', 'start', 'cromwell'])

def install_cromwell_config():
    """Transfer Cromwell .conf file from instance info to local file."""
    fn = os.path.join(CONFIG_DIR, CROMWELL_CONF)
    if os.path.exists(fn):
        print("Already installed cromwell config...SKIPPING")
    else:
        sys.stdout.write("Install cromwell config...")
        with open(fn, 'w') as f:
            f.write(fetch_instance_info(name=DOT_CONF_TAG))


if __name__ == '__main__':
    create_directories()
    install_packages()
    install_cromwell()
    install_cromwell_config()
    add_cromwell_profile()
    add_and_start_cromwell_service()
    print("Startup script...DONE")
