import os
import ruamel.yaml
from copy import deepcopy
from google.cloud import storage
from pathlib import Path

# TODO: strip cwd from beginning of path. i.e. /gscmnt/gc2560/core/... removed
# TODO: files should be relative to specifying file, not cwd
# TODO: collapse file structure somehow? worry about name collisions
# TODO: bring in bucket, inputs, definition as args
# TODO: make UNIQUE_PATH somethings actually unique
# TODO: paths should not be relative when they're used to make a GCS path

BUCKET_NAME = "griffith-lab-cromwell"
INPUTS_FILE = Path('../analysis-workflows/example_data/rnaseq/workflow.yaml')
DEFINITION_FILE = Path('../analysis-workflows/definitions/pipelines/rnaseq.cwl')
UNIQUE_PATH = "2021-03-22"

bucket = storage.Client().bucket(BUCKET_NAME)
yaml = ruamel.yaml.YAML()

def upload_to_gcs(src, dest):
    """Upload a local file to GCS. src is a filepath/name and dest is target GCS name."""
    print(f"Uploading {src} to {dest}")
    # bucket.blob(dest).upload_from_filename(src, num_retries=3)
    return f"gs://{bucket.name}/{dest}"


def secondary_file_path(basepath, suffix):
    if suffix.startswith("^"):
        return secondary_file_path(basepath.stem, suffix[1:])
    else:
        return f"{basepath}{suffix}"


def upload_secondary_file(basepath, secondary_file):
    filepath = secondary_file_path(basepath, secondary_file)
    # This bucket path is going to get _very_ deep and most nesting will be inconsequential
    # we can collapse this later, somehow
    upload_to_gcs(filepath, f"workflow-inputs/{UNIQUE_PATH}/{filepath}")


def upload_secondary_files(basepath, secondary_files):
    # Not supporting expression for now. Maybe later.
    if isinstance(secondary_files, str):
        upload_secondary_file(basepath, secondary_files)
    else:
        for file_suffix in secondary_files:
            upload_secondary_file(basepath, file_suffix)


def walk_object(obj, node_fn, key=None):
    """Walk an objects structure, applying node_fn to each node, both branch and leaf nodes.
    node_fn must accept both the node and a kwarg for key."""
    if (isinstance(obj, dict)):
        return node_fn({ k: walk_object(v, node_fn, key=k) for k, v in obj.items() }, key=key)
    elif (isinstance(obj, list)):
        return node_fn([ walk_object(x, node_fn, key=None) for x in obj ], key=key)
    else:  # all non-collection classes are treated as leaf nodes
        return node_fn(obj, key=key)


def get(coll, k):
    try:
        return coll[k]
    except (KeyError, IndexError):
        return None


def get_in(coll, path):
    if not path:   return coll
    elif not coll: return None
    else:          return get_in(get(coll, path[0]), path[1:])


def cloudize_file_path(path):
    return Path(path.parent, Path(f"{path.stem}_cloud{path.suffix}"))


class Workflow:
    def __init__(self, inputs_file, definition_cwl):
        self.inputs_path = Path(inputs_file)
        self.inputs = yaml.load(Path(inputs_file))
        self.definition = yaml.load(Path(definition_cwl))
        self.cloudized_inputs = None

    def _cloudize_file_node(self, node, key):
        """Modify a File node by uploading to GCS and pointing path to its new location."""
        if (secondary_files := get_in(self.definition, ['inputs', key, 'secondaryFiles'])):
            upload_secondary_files(node.get('path'), secondary_files)
        # TODO: relative paths will probably throw a wrench in this
        # cloud_path = upload_to_gcs(node.get('path'), f"workflow-inputs/{UNIQUE_PATH}/{node.path}")

        # dont want to mutate self.inputs by mutating a contained node
        return node.copy()  # .update({'path': cloud_path})

    def _cloudize_node(self, node, key):
        if (isinstance(node, dict) and node.get('class') == 'File'):
            return self._cloudize_file_node(node, key)
        else:
            return node

    def cloudize(self):
        self.cloudized_inputs = walk_object(self.inputs, self._cloudize_node)
        # yaml.dump(self.cloudized_inputs, cloudize_file_path(inputs_path))
        return self.cloudized_inputs


wf = Workflow(INPUTS_FILE, DEFINITION_FILE)
if __name__ == '__main__':
    wf.cloudize()
