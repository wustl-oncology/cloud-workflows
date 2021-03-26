import os
from argparse import ArgumentParser
from ruamel.yaml import YAML
from copy import deepcopy
from datetime import date
from getpass import getuser
from google.cloud import storage
from pathlib import Path

# IMPROVE: be able to drop and pick up the upload somehow. long running process, may break near end

UNIQUE_PATH = f"input_data/{getuser()}/" + date.today().strftime("%Y-%m-%d")


# ---- GCS interactions ------------------------------------------------

def upload_to_gcs(bucket, src, dest):
    """Upload a local file to GCS. src is a filepath/name and dest is target GCS name."""
    if os.path.exists(src):
        print(f"Uploading {src} to {dest}")
        # bucket.blob(dest).upload_from_filename(src, num_retries=3)
    else:
        print(f"WARN: could not find source file, potentially just a basepath: {src}")


# ---- Generic functions -----------------------------------------------

def walk_object(obj, node_fn, path=[]):
    """Walk an objects structure, applying node_fn to each node, both branch and leaf nodes.
    node_fn must accept both the node and a kwarg for path."""
    if (isinstance(obj, dict)):
        return node_fn({ k: walk_object(v, node_fn, path=(path.copy() + [k]))
                         for k, v in obj.items() },
                       path)
    elif (isinstance(obj, list)):
        return node_fn([ walk_object(x, node_fn, path=(path.copy() + [i]))
                         for i, x in enumerate(obj) ],
                       path)
    else:  # all non-collection classes are treated as leaf nodes
        return node_fn(obj, path)


# modified from https://stackoverflow.com/a/10579695
def set_in(coll, path, val):
    """Mutable deep assignment to a collection."""
    for x in path:
        if not get(coll, x):
            coll[x] = {}
        prev, coll = coll, get(coll, x)
    prev[x] = val


def get(coll, k):
    """Safe retrieval from a collection, returns None instead of Error."""
    try:
        return coll[k]
    except (KeyError, IndexError):
        return None


def get_in(coll, path):
    """Safe deep retrieval from a collection, returns None instead of Error."""
    if not path:   return coll
    elif not coll: return None
    else:          return get_in(get(coll, path[0]), path[1:])


# ---- Pathlib ---------------------------------------------------------

def deepest_shared_ancestor(paths):
    ancestors = [set(path.resolve().parents) for path in paths]
    shared_ancestors = ancestors[0].intersection(*ancestors[1:])
    return max(shared_ancestors, key=lambda x: len(str(x)))


def is_ancestor(path, ancestor):
    return ancestor in set(path.resolve().parents)


def strip_ancestor(path, ancestor):
    if is_ancestor(path, ancestor):
        return path.resolve().relative_to(ancestor)
    else:  # absolute path if not an ancestor
        return path.resolve()

def expand_relative(path, base_path):
    if path.is_absolute():
        return path
    else:
        return Path(f"{base_path}/{path}")


# ---- CWL specific ----------------------------------------------------

def secondary_file_suffixes(cwl_definition, input_name):
    return get_in(cwl_definition, ['inputs', input_name, 'secondaryFiles'])


def secondary_file_path(basepath, suffix):
    if suffix.startswith("^"):
        return secondary_file_path(basepath.stem, suffix[1:])
    else:
        return Path(str(basepath) + suffix)


def secondary_file_paths(base_path, suffixes):
    if isinstance(suffixes, str):
        return [secondary_file_path(base_path, suffixes)]
    else:
        return [secondary_file_path(base_path, suffix) for suffix in suffixes]


# ---- Actually do the work we want ------------------------------------

class FilePath:
    def __init__(self, local):
        self.local = local
        self.cloud = None

    def set_cloud(self, cloud):
        self.cloud = f"{UNIQUE_PATH}/{cloud}"


class FileInput:
    def __init__(self, file_path, yaml_path, secondary_file_suffixes=[]):
        self.file_path = FilePath(file_path)
        self.yaml_path = yaml_path
        self.secondary_files = [ FilePath(f) for f in secondary_file_paths(file_path, secondary_file_suffixes)]
        self.all_file_paths = [self.file_path] + self.secondary_files


def parse_file_inputs(cwl_definition, wf_inputs, base_path):
    """Crawl a yaml.loaded CWL definition structure and workflow inputs files for input Files."""
    # build inputs list from original crawl
    file_inputs = []
    def process_node(node, node_path):
        if (isinstance(node, dict) and node.get('class') == 'File'):
            file_path = expand_relative(Path(node.get('path')), base_path)
            if (suffixes := secondary_file_suffixes(cwl_definition, node_path[-1])):
                file_inputs.append(FileInput(file_path, node_path, suffixes))
            else:
                file_inputs.append(FileInput(file_path, node_path))
        return node
    walk_object(wf_inputs, process_node)

    # Postprocessing: add cloud path to file_inputs
    ancestor = deepest_shared_ancestor([file_path.local for f in file_inputs for file_path in f.all_file_paths])
    for f in file_inputs:
        for file_path in f.all_file_paths:
            file_path.set_cloud(strip_ancestor(file_path.local, ancestor))

    return file_inputs


def cloudize(bucket, cwl_path, inputs_path, output_path):
    """Generate a cloud version of an inputs YAML file provided that file
and its workflow's CWL definition."""
    yaml = YAML()

    # load+parse files
    wf_inputs = yaml.load(inputs_path)
    cwl_definition = yaml.load(cwl_path)
    file_inputs = parse_file_inputs(cwl_definition, wf_inputs, inputs_path.parent)

    # Generate new YAML file
    new_yaml = deepcopy(wf_inputs)
    for f in file_inputs:
        set_in(new_yaml, f.yaml_path + ['path'] , str(f"gs://{bucket.name}/{f.file_path.cloud}"))
    yaml.dump(new_yaml, output_path)
    print(f"Yaml dumped to {output_path}")

    # Upload all the files
    for f in file_inputs:
        for file_path in f.all_file_paths:
            upload_to_gcs(bucket, file_path.local, file_path.cloud)
    print("Completed file upload process.")


# ---- CLI pieces ------------------------------------------------------

def default_output(inputs_filename):
    path = Path(inputs_filename)
    return f"{path.parent}/{path.stem}_cloud{path.suffix}"


if __name__=="__main__":
    parser = ArgumentParser(description="Prepare a CWL workload for cloud processing. Upload Files and generate new inputs.yaml.")
    parser.add_argument("bucket",
                        help="the name of the GCS bucket to upload workflow inputs")
    parser.add_argument("workflow_definition",
                        help="path to the .cwl file defining your workflow")
    parser.add_argument("workflow_inputs",
                        help="path to the .yaml file specifying your workflow inputs")
    parser.add_argument("-o", "--output",
                        help="path to write the updated workflow inputs, defaults to the value of workflow_inputs with _cloud before the extension.")
    args = parser.parse_args()

    cloudize(
        storage.Client().bucket(args.bucket),
        Path(args.workflow_definition),
        Path(args.workflow_inputs),
        Path(args.output or default_output(args.workflow_inputs))
    )
