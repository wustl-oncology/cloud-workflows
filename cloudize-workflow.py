from ruamel.yaml import YAML
from copy import deepcopy
from google.cloud import storage
from pathlib import Path

# TODO: bring in bucket, inputs, definition as args
# TODO: make UNIQUE_PATH somethings actually unique
# TODO: files should be relative to specifying file, not cwd
# TODO: strip cwd from beginning of path. i.e. /gscmnt/gc2560/core/... removed
# TODO: collapse file structure somehow? worry about name collisions
# TODO: paths should not be relative when they're used to make a GCS path

BUCKET_NAME = "griffith-lab-cromwell"
INPUTS_FILE = '../analysis-workflows/example_data/rnaseq/workflow.yaml'
DEFINITION_FILE = '../analysis-workflows/definitions/pipelines/rnaseq.cwl'
UNIQUE_PATH = "2021-03-22"

bucket = storage.Client().bucket(BUCKET_NAME)
yaml = YAML()


# ---- GCS interactions ------------------------------------------------

def upload_to_gcs(src, dest):
    """Upload a local file to GCS. src is a filepath/name and dest is target GCS name."""
    if os.path.exists(src):
        print(f"Uploading {src} to {dest}")
        # bucket.blob(dest).upload_from_filename(src, num_retries=3)
        return f"gs://{bucket.name}/{dest}"
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


# https://stackoverflow.com/a/10579695
def update_in(coll, path, func):
    """Mutable deep update to a collection."""
    for x in path:
        if not get(coll, x):
            coll[x] = {}
        prev, coll = coll, get(coll, x)
    prev[x] = func(prev[x])


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


# ---- CWL specific ----------------------------------------------------

def secondary_file_path(basepath, suffix):
    if suffix.startswith("^"):
        return secondary_file_path(basepath.stem, suffix[1:])
    else:
        return f"{basepath}{suffix}"


def secondary_file_paths(base_path, suffixes):
    if isinstance(suffixes, str):
        return [secondary_file_path(base_path, suffixes)]
    else:
        return [secondary_file_path(base_path, suffix) for suffix in suffixes]


def cloudize_file_path(path):
    path = Path(path)
    return Path(path.parent, Path(f"{path.stem}_cloud{path.suffix}"))


class FileInput:
    def __init__(self, file_path, yaml_path, secondary_file_suffixes=[]):
        self.file_path = file_path
        self.yaml_path = yaml_path
        self.secondary_files = secondary_file_paths(file_path, secondary_file_suffixes)


class Workflow:
    def __init__(self, inputs_file, definition_cwl):
        self.inputs_path = Path(inputs_file)
        self.inputs = yaml.load(Path(inputs_file))
        self.definition = yaml.load(Path(definition_cwl))
        # File inputs are tracked separately instead of modified in place so
        # renaming logic can be performed in aggregate.
        self._file_inputs = []

    # mutates internal state
    def _track_file_node(self, node, node_path):
        """Modify a File node by uploading to GCS and pointing path to its new location."""
        file_path = node.get('path')
        if (suffixes := get_in(self.definition, ['inputs', node_path[-1], 'secondaryFiles'])):
            print(f"Found secondaryFiles for {node_path} {file_path}: {suffixes}")
            self._file_inputs.append(FileInput(file_path, node_path, suffixes))
        else:
            print(f"Did not find secondaryFiles for {node_path} {file_path}")
            self._file_inputs.append(FileInput(file_path, node_path))

    def _track_file_inputs(self):
        def process_node(node, path):
            if (isinstance(node, dict) and node.get('class') == 'File'):
                self._track_file_node(node, path)
            return node
        walk_object(self.inputs, process_node)

    def _upload_files(self):
        for file_input in self._file_inputs:
            src_path = file_input.file_path
            upload_to_gcs(src_path, cloudize_file_path(src_path))
            for full_path in file_input.secondary_files:
                upload_to_gcs(full_path, cloudize_file_path(full_path))

    def _generate_new_yaml(self):
        """Create a new YAMl structure (not file) from current Workflow state."""
        new_yaml = deepcopy(self.inputs)
        for file_input in self._file_inputs:
            def add_keys(x):
                x['path'] = file_input.file_path
                return x
            update_in(new_yaml, file_input.yaml_path, add_keys)
        return new_yaml

    def cloudize(self):
        self._track_file_inputs()
        # find cloud paths
        target_path = cloudize_file_path(self.inputs_path)
        print(f"Yaml dumped to {target_path}")
        yaml.dump(self._generate_new_yaml(), target_path)
        self._upload_files()
        print("Completed file upload process.")


def cloud_paths(file_paths):
    # check for colliding file names
    # if there are colliding filenames, expand them to include parent
    # expand all paths which share one of those parents
    # return gs://bucket/new_path for all paths
    pass


wf = Workflow(INPUTS_FILE, DEFINITION_FILE)
if __name__ == '__main__':
    wf.cloudize()
