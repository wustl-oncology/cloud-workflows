# third-party, pip install
import WDL  # https://miniwdl.readthedocs.io/en/latest/WDL.html#
from ruamel.yaml import YAML
from google.cloud import storage
# built-in, hooray
import os
from argparse import ArgumentParser
from copy import deepcopy
from datetime import date
from getpass import getuser
from pathlib import Path

# IMPROVE: be able to drop and pick up the upload somehow.
# long running process, may break near end

UNIQUE_PATH = f"input_data/{getuser()}/" + date.today().strftime("%Y-%m-%d")
yaml = YAML()


# ---- GCS interactions ------------------------------------------------

def upload_to_gcs(bucket, src, dest, dryrun=False):
    """Upload a local file to GCS bucket. src is a filepath and dest is target GCS name."""
    if os.path.isdir(src):
        print(f"Source file {src} is a directory. Skipping.")
    elif os.path.isfile(src):
        print(f"Uploading {src} to {dest}")
        if not dryrun:
            # TODO: just use gsutil, behavior discrepancies, e.g. with .interval_list
            bucket.blob(dest).upload_from_filename(src, num_retries=3)
    else:
        print(f"WARN: could not find source file, potentially just a basepath: {src}")


# ---- Generic functions -----------------------------------------------

def walk_object(obj, node_fn, path=[]):
    """Walk an objects structure, applying node_fn to each node, both
    branch and leaf nodes.
    node_fn must accept both the node and a kwarg for path.
    """
    if (isinstance(obj, dict)):
        return node_fn({k: walk_object(v, node_fn, path=(path.copy() + [k]))
                        for k, v in obj.items()},
                       path)
    elif (isinstance(obj, list)):
        return node_fn([walk_object(x, node_fn, path=(path.copy() + [i]))
                        for i, x in enumerate(obj)],
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
        if isinstance(coll, dict) or isinstance(coll, list):
            return coll[k]
        else:
            return None
    except (KeyError, IndexError):
        return None


def get_in(coll, path):
    """Safe deep retrieval from a collection, returns None instead of Error."""
    if not path:
        return coll
    elif not coll:
        return None
    else:
        return get_in(get(coll, path[0]), path[1:])


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


# ---- YAML specific ---------------------------------------------------


def input_name(node_path):
    inp = node_path and node_path[-1]
    if isinstance(inp, int):
        inp = node_path[-2]
    return inp


def is_file_input(node, node_parent, input_file_path):
    """Check if a node is a file input, either object class File or existing filepath string."""
    explicitly_defined = isinstance(node, dict) and node.get('class') == 'File'
    matches_filename = isinstance(node, str) and node_parent != 'path' \
        and os.path.exists(expand_relative(Path(node), input_file_path))
    return (explicitly_defined or matches_filename)


def get_path(node):
    """ Get path value of a File node, works for both objects and strings."""
    if isinstance(node, dict):
        return Path(node.get('path'))
    else:
        return Path(node)


def set_path(yaml, file_input, new_value):
    """Set the path value for `file_input` within `yaml`.
    Works for both objects and strings."""
    if get_in(yaml, file_input.input_path + ['path']):
        set_in(yaml, file_input.input_path + ['path'], new_value)
    else:
        set_in(yaml, file_input.input_path, new_value)


# ---- WDL specific ----------------------------------------------------

def load_wdl_definition(wdl_path):
    deps_paths = [str(wdl_path.parent), str(wdl_path.parent.parent)]
    return WDL.load(str(wdl_path), deps_paths)


def prepend_workflow_name(obj, wdl_definition):
    def idempotent_prepend(s, prefix):
        """Prepend a . prefix iff no . prefix already exists."""
        if len(s.split(".")) == 1:
            return f"{prefix}.{s}"
        else:
            return s
    wf_name = wdl_definition.workflow.name
    return {idempotent_prepend(k, wf_name): v for k, v in obj.items()}


def find_file_inputs_wdl(wf_inputs, inputs_file_path):
    file_inputs = []

    def process_node(node, node_path):
        if (is_file_input(node, input_name(node_path), inputs_file_path)):
            file_path = expand_relative(get_path(node), inputs_file_path)
            file_inputs.append(FileInput(file_path, node_path))
        else:
            print(f"not file_input node={node} input_name({node_path}) => {input_name(node_path)}")
        return node

    walk_object(wf_inputs, process_node)
    return file_inputs


# ---- CWL specific ----------------------------------------------------

def secondary_file_suffixes(cwl_definition, yaml_input_name):
    return get_in(cwl_definition, ['inputs', yaml_input_name, 'secondaryFiles']) or []


def secondary_file_path(basepath, suffix):
    if suffix.startswith("^"):
        return secondary_file_path(f"{basepath.parent}/{basepath.stem}", suffix[1:])
    else:
        return Path(str(basepath) + suffix)


def secondary_file_paths(base_path, suffixes):
    if isinstance(suffixes, str):
        return [secondary_file_path(base_path, suffixes)]
    else:
        return [secondary_file_path(base_path, suffix) for suffix in suffixes]


def find_file_inputs_cwl(wf_path, wf_inputs, inputs_file_path):
    """Crawl a yaml.loaded CWL structure and workflow inputs files for input Files."""
    cwl_definition = yaml.load(wf_path)
    file_inputs = []

    def process_node(node, node_path):
        if (is_file_input(node, input_name(node_path), inputs_file_path)):
            file_path = expand_relative(get_path(node), inputs_file_path)
            suffixes = secondary_file_suffixes(cwl_definition, input_name(node_path))
            secondary_files = [FilePath(f) for f in secondary_file_paths(file_path, suffixes)]
            file_inputs.append(FileInput(file_path, node_path, secondary_files))
        return node

    walk_object(wf_inputs, process_node)
    return file_inputs


# ---- Actually do the work we want ------------------------------------

class FilePath:
    def __init__(self, local):
        self.local = local.resolve()
        self.cloud = None

    def set_cloud(self, cloud):
        self.cloud = f"{UNIQUE_PATH}/{cloud}"


class FileInput:
    def __init__(self, file_path, input_path, secondary_files=[]):
        self.file_path = FilePath(file_path)
        self.input_path = input_path
        self.secondary_files = secondary_files
        self.all_file_paths = [self.file_path] + self.secondary_files


def parse_file_inputs(wf_path, wf_inputs, inputs_file_path):
    # build inputs list from original crawl
    if wf_path.suffix == ".cwl":
        file_inputs = find_file_inputs_cwl(wf_path, wf_inputs, inputs_file_path)
    else:
        file_inputs = find_file_inputs_wdl(wf_inputs, inputs_file_path)

    # Postprocessing: add cloud path to file_inputs
    ancestor = deepest_shared_ancestor([file_path.local
                                        for f in file_inputs
                                        for file_path in f.all_file_paths])
    for f in file_inputs:
        for file_path in f.all_file_paths:
            file_path.set_cloud(strip_ancestor(file_path.local, ancestor))

    return file_inputs


def cloudize(bucket, wf_path, inputs_path, output_path, dryrun=False):
    """Generate a cloud version of an inputs YAML file provided that file
    and its workflow's CWL definition."""

    # load+parse files
    wf_inputs = yaml.load(inputs_path)
    file_inputs = parse_file_inputs(wf_path, wf_inputs, inputs_path.parent)

    # Generate new inputs file
    new_input_obj = deepcopy(wf_inputs)
    for f in file_inputs:
        set_path(new_input_obj, f, str(f"gs://{bucket.name}/{f.file_path.cloud}"))

    if wf_path.suffix == ".wdl":
        wdl_definition = load_wdl_definition(wf_path)
        new_input_obj = prepend_workflow_name(new_input_obj, wdl_definition)

    yaml.dump(new_input_obj, output_path)
    print(f"Yaml dumped to {output_path}")

    # Upload all the files
    # TODO: find a way to optimize/parallelize a la `gsutil -m
    for f in file_inputs:
        for file_path in f.all_file_paths:
            upload_to_gcs(bucket, file_path.local, file_path.cloud, dryrun=dryrun)
    print("Completed file upload process.")


# ---- CLI pieces ------------------------------------------------------

def default_output(inputs_filename):
    path = Path(inputs_filename)
    return f"{path.parent}/{path.stem}_cloud{path.suffix}"


if __name__ == "__main__":
    parser = ArgumentParser(description="Prepare a CWL workload for cloud processing. Upload Files and generate new inputs.yaml.")
    parser.add_argument("bucket",
                        help="the name of the GCS bucket to upload workflow inputs")
    parser.add_argument("workflow_definition",
                        help="path to the .cwl file defining your workflow")
    parser.add_argument("workflow_inputs",
                        help="path to the .yaml file specifying your workflow inputs")
    parser.add_argument("-o", "--output",
                        help="path to write the updated workflow inputs, defaults to the value of workflow_inputs with _cloud before the extension.")
    parser.add_argument("--dryrun", help="prevent actual upload to GCS.")
    args = parser.parse_args()

    cloudize(
        storage.Client().bucket(args.bucket),
        Path(args.workflow_definition),
        Path(args.workflow_inputs),
        Path(args.output or default_output(args.workflow_inputs)),
        dryrun=args.dryrun
    )
