from ruamel.yaml import YAML
from copy import deepcopy
from google.cloud import storage
from pathlib import Path

# TODO: bring in bucket, inputs, definition as args
# TODO: make UNIQUE_PATH somethings actually unique

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
        target = f"{UNIQUE_PATH}/{dest}"
        print(f"Uploading {src} to {target}")
        # bucket.blob(target).upload_from_filename(src, num_retries=3)
        return f"gs://{bucket.name}/{target}"
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


# ---- Pathlib ---------------------------------------------------------

def deepest_shared_ancestor(paths):
    ancestors = [set(path.resolve().parents) for path in paths]
    shared_ancestors = ancestors[0].intersection(*ancestors[1:])
    return max(shared_ancestors, key=lambda x: len(str(x)))


# ---- CWL specific ----------------------------------------------------

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
        file_path = Path(node.get('path'))
        if (suffixes := get_in(self.definition, ['inputs', node_path[-1], 'secondaryFiles'])):
            self._file_inputs.append(FileInput(file_path, node_path, suffixes))
        else:
            self._file_inputs.append(FileInput(file_path, node_path))

    def _track_file_inputs(self):
        def process_node(node, path):
            if (isinstance(node, dict) and node.get('class') == 'File'):
                self._track_file_node(node, path)
            return node
        walk_object(self.inputs, process_node)

    def _upload_files(self):
        ancestor = deepest_shared_ancestor([f.file_path for f in self._file_inputs])

        for file_input in self._file_inputs:
            src_path = file_input.file_path
            upload_to_gcs(src_path, src_path.resolve().relative_to(ancestor))
            for full_path in file_input.secondary_files:
                upload_to_gcs(full_path, full_path.resolve().relative_to(ancestor))

    def _generate_new_yaml(self):
        """Create a new YAMl structure (not file) from current Workflow state."""
        new_yaml = deepcopy(self.inputs)
        for file_input in self._file_inputs:
            def add_keys(x):
                x['path'] = str(file_input.file_path)
                return x
            update_in(new_yaml, file_input.yaml_path, add_keys)
        return new_yaml

    def cloudize(self):
        self._track_file_inputs()
        # find cloud paths
        target_path = Path(self.inputs_path.parent,
                           Path(f"{self.inputs_path.stem}_cloud{self.inputs_path.suffix}"))
        print(f"Yaml dumped to {target_path}")
        yaml.dump(self._generate_new_yaml(), target_path)
        self._upload_files()
        print("Completed file upload process.")


wf = Workflow(INPUTS_FILE, DEFINITION_FILE)
if __name__ == '__main__':
    wf.cloudize()
