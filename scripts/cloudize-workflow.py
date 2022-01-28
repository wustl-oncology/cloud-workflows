# third-party, pip install
import WDL as wdl  # https://miniwdl.readthedocs.io/en/latest/WDL.html#
from ruamel.yaml import YAML
# built-in, hooray
import json
import os
from argparse import ArgumentParser
from copy import deepcopy
from datetime import date
from getpass import getuser
from pathlib import Path


# TODO: if string type, wrap with quotes
# IMPROVE: be able to drop and pick up the upload somehow.
# long running process, may break near end

UNIQUE_PATH = f"input_data/{getuser()}/" + date.today().strftime("%Y-%m-%d")
yaml = YAML()
yaml.width = float("Infinity")  # prevent line wrapping
yaml.preserve_quotes = True

# ---- GCS interactions ------------------------------------------------

def upload_to_gcs(bucket, src, dest, dryrun=False):
    """Upload a local file to GCS bucket. src is a filepath and dest is target GCS name."""
    gcs_uri = f"gs://{bucket}/{dest}"
    if os.path.isdir(src):
        print(f"Source file {src} is a directory. Skipping.")
    elif not os.path.isfile(src):
        print(f"WARN: could not find source file, potentially just a basepath: {src}")
    elif dryrun:
        pass
    else:
        os.system(f"gsutil cp -n {src} {gcs_uri}")


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
    ancestors = [set(path.parents) for path in paths]
    if ancestors:
        shared_ancestors = ancestors[0].intersection(*ancestors[1:])
        return max(shared_ancestors, key=lambda x: len(str(x)))
    else:
        return None


def is_ancestor(path, ancestor):
    return ancestor in set(path.parents)


def strip_ancestor(path, ancestor):
    if is_ancestor(path, ancestor):
        return path.relative_to(ancestor)
    else:  # absolute path if not an ancestor
        return path


def expand_relative(path, base_path):
    if path.is_absolute():
        return path
    else:
        return Path(f"{base_path}/{path}")


# ---- Inputs Object specific ---------------------------------------------------


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


# ---- Workflow Language Classes ---------------------------------------

class WorkflowLanguage:
    def __init__(self, definition_path, inputs_path):
        self.definition_path = definition_path
        self.inputs_path = inputs_path
        self.inputs = yaml.load(inputs_path)

    def find_file_inputs(self):
        file_inputs = []

        def process_node(node, node_path):
            if (is_file_input(node, input_name(node_path), self.inputs_path.parent)):
                file_path = expand_relative(get_path(node), self.inputs_path.parent)
                file_inputs.append(FileInput(node_path, file_path))
            return node
        walk_object(self.inputs, process_node)
        return file_inputs


class WDL(WorkflowLanguage):
    def __init__(self, definition_path, inputs_path):
        super().__init__(definition_path, inputs_path)
        path_dir = definition_path.parent
        self.definition = wdl.load(str(definition_path), [str(path_dir), str(path_dir.parent)])
        root = self.definition.workflow or self.definition.tasks[0]
        self.inputs = WDL.prefix_inputs(self.inputs, self.definition.workflow.name)
        # validate inputs
        missing_inputs = [f"{root.name}.{inp.name}"
                          for inp in root.required_inputs
                          if not f"{root.name}.{inp.name}" in self.inputs]
        if missing_inputs:
            raise Exception(f"Missing required inputs", missing_inputs)

    def prefix_inputs(inputs, prefix):
        def prepend(s, p):
            return f"{p}.{s}" if len(s.split(".")) == 1 else s
        prefixed = inputs.copy()
        for k, v in inputs.items():
            del prefixed[k]
            prefixed[prepend(k, prefix)] = v
        return prefixed


class CWL(WorkflowLanguage):
    def __init__(self, definition_path, inputs_path):
        super().__init__(definition_path, inputs_path)
        self.definition = yaml.load(definition_path)

    def _file_input(self, file_path, node_path):
        suffixes = self.secondary_file_suffixes(input_name(node_path))
        secondary_files = [FilePath(f) for f in CWL.secondary_file_paths(file_path, suffixes)]
        return FileInput(node_path, file_path, secondary_files)

    def secondary_file_suffixes(self, yaml_input_name):
        return get_in(self.definition, ['inputs', yaml_input_name, 'secondaryFiles']) or []

    def secondary_file_path(basepath, suffix):
        if suffix.startswith("^"):
            return CWL.secondary_file_path(f"{basepath.parent}/{basepath.stem}", suffix[1:])
        else:
            return Path(str(basepath) + suffix)

    def secondary_file_paths(base_path, suffixes):
        if isinstance(suffixes, str):
            return [CWL.secondary_file_path(base_path, suffixes)]
        else:
            return [CWL.secondary_file_path(base_path, suffix) for suffix in suffixes]


def make_workflow(definition_path, inputs_path):
    if definition_path.suffix == ".cwl":
        return CWL(definition_path, inputs_path)
    else:
        return WDL(definition_path, inputs_path)


# ---- Actually do the work we want ------------------------------------

class FilePath:
    def __init__(self, local):
        self.local = local
        self.cloud = None

    def set_cloud(self, cloud):
        self.cloud = f"{UNIQUE_PATH}/{cloud}"

    def __repr__(self):
        return f"FilePath(\"{str(self.local)}\")"


class FileInput:
    def __init__(self, input_path, file_path, secondary_files=[]):
        self.file_path = FilePath(file_path)
        self.input_path = input_path
        self.secondary_files = secondary_files
        self.all_file_paths = [self.file_path] + self.secondary_files

    def __repr__(self):
        return f"FileInput(input_path=\"{str(self.input_path)}\", file_path=\"{str(self.file_path)}\")"


def set_cloud_paths(file_inputs):
    """Set cloud paths for all file_inputs, mutating them."""
    ancestor = deepest_shared_ancestor([file_path.local
                                        for f in file_inputs
                                        for file_path in f.all_file_paths])
    for f in file_inputs:
        for file_path in f.all_file_paths:
            file_path.set_cloud(strip_ancestor(file_path.local, ancestor))


def cloudize_file_paths(inputs, bucket, file_inputs):
    new_input_obj = deepcopy(inputs) or {}
    for f in file_inputs:
        set_in(new_input_obj, f.input_path, str(f"gs://{bucket}/{f.file_path.cloud}"))
    return new_input_obj


def write_new_inputs(new_input_obj, output_path):
    """Write a Python object to a file. Defaults to YAML format unless output_path ends .json"""
    if output_path.suffix == ".json":
        with open(output_path, 'w+') as f:
            json.dump(new_input_obj, f)
    else:
        yaml.dump(new_input_obj, output_path)
    print(f"Inputs dumped to {output_path}")


def upload_all(file_inputs, bucket, dryrun):
    # Upload all the files
    # TODO: find a way to optimize/parallelize a la `gsutil -m
    for f in file_inputs:
        for file_path in f.all_file_paths:
            upload_to_gcs(bucket, file_path.local, file_path.cloud, dryrun=dryrun)


def cloudize(bucket, wf_path, inputs_path, output_path, dryrun=False):
    """Generate a cloud version of an inputs YAML file provided that file
    and its workflow's CWL definition."""
    workflow = make_workflow(wf_path, inputs_path)
    file_inputs = workflow.find_file_inputs()
    set_cloud_paths(file_inputs)
    cloudized_inputs = cloudize_file_paths(workflow.inputs, bucket, file_inputs)
    write_new_inputs(cloudized_inputs, output_path)
    upload_all(file_inputs, bucket, dryrun)
    print("Completed file upload process.")


# ---- CLI pieces ------------------------------------------------------

def default_output(inputs_filename):
    path = Path(inputs_filename)
    return f"{path.parent}/{path.stem}_cloud{path.suffix}"


if __name__ == "__main__":
    parser = ArgumentParser(description="""Prepare a CWL workload for cloud processing.
Upload File inputs and generate new workflow_inputs file.""")

    parser.add_argument("bucket",
                        help="the name of the GCS bucket to upload workflow inputs")
    parser.add_argument("workflow_definition",
                        help="path to the .cwl file defining your workflow")
    parser.add_argument("workflow_inputs",
                        help="path to the YAML formatted file specifying your workflow inputs")
    parser.add_argument("-o", "--output",
                        help="""Path to write the updated workflow inputs.
Defaults to workflow_inputs with _cloud before the extension.
If this value ends with .json, JSON format used instead of YAML.""")

    parser.add_argument("--dryrun", help="prevent actual upload to GCS.")
    args = parser.parse_args()

    cloudize(
        args.bucket,
        Path(args.workflow_definition),
        Path(args.workflow_inputs),
        Path(args.output or default_output(args.workflow_inputs)),
        dryrun=args.dryrun
    )
