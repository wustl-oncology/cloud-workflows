import os
import ruamel.yaml
from copy import deepcopy
from google.cloud import storage
from pathlib import Path

BUCKET_NAME = "griffith-lab-cromwell"
INPUTS_FILE = Path('../my-workflows/rnaseq/inputs.yaml')
DEFINITION_FILE = Path('../my-workflows/rnaseq/workflow.cwl')
UNIQUE_PATH = "2021-03-22"  # TODO: make this a random uuid, user+time, or something

bucket = storage.Client().bucket(BUCKET_NAME)
yaml = ruamel.yaml.YAML()


def upload_to_gcs(src, dest):
    """Upload a local file to GCS. src is a filepath/name and dest is target GCS name."""
    print(f"Uploading {src} to {dest}")
    bucket.blob(dest).upload_from_filename(src, num_retries=3)
    return f"gs://{bucket.name}/{dest}"


def secondary_file_path(basepath, suffix):
    if suffix.beginswith("^"):
        return secondary_file_path(basepath.stem, suffix[1:])
    else:
        return f"{basepath}{suffix}"


def upload_secondary_file(basepath, secondary_file):
    filepath = secondary_file_path(basepath, secondary_file)
    # This bucket path is going to get _very_ big and most nesting will be inconsequential
    # we can collapse this later, somehow
    upload_to-gcs(filepath, f"workflow-inputs/{UNIQUE_PATH}/{filepath}")


def upload_secondary_files(basepath, secondary_files):
    # Not supporting expression for now. Maybe later.
    if isinstance(secondary_files, str):
        upload_secondary_file(basepath, secondary_files)
    else:
        for file_suffix in secondary_files:
            upload_secondary_file(basepath, file_suffix)


# TODO: CHECK THIS
def walk_object(obj, node_fn, key=None):
    """Walk an objects structure, applying node_fn to each node, both branch and leaf nodes.
    node_fn must accept both the node and a kwarg for key."""
    if (isinstance(obj, dict)):
        return node_fn({ k: walk_object(v, node_fn, key=k) for k, v in obj.items() }, key=key)
    elif (isinstance(obj, list)):
        return node_fn([ walk_object(x, node_fn) for x in obj ], key=key)
    else:  # all non-collection classes are treated as leaf nodes
        node_fn(obj, key=key)


def get_in(coll, path):
    if not path:   return coll
    elif not coll: return None
    else:          return get_in(coll[path[0]], path[1:])


def cloudize_file_path(path):
    return Path(path.parent, Path(f"{path.stem}_cloud{path.suffix}"))


class Workflow:
    def __init__(self, inputs_file, definition_cwl):
        self.inputs_path = Path(inputs_file)
        self.inputs = yaml.load(Path(inputs_file))
        self.definition = yaml.load(Path(definition_cwl))
        self.cloudized_inputs = None

    def _cloudize_file_node(self, node, key=None):
        """Modify a File node by uploading to GCS and pointing path to its new location."""
        if (secondary_files := get_in(self.definition, ['inputs', key, 'secondaryFiles'])):
            upload_secondary_files(node.path, secondary_files)
        # TODO: relative paths will probably throw a wrench in this
        cloud_path = upload_to_gcs(node.path, f"workflow-inputs/{UNIQUE_PATH}/{node.path}")
        # dont want to mutate self.inputs by mutating a contained node
        return node.copy().update({'path': cloud_path})

    def _print_file_node(self, node, key=None):
        print(f"key={key} type={type(node)} class={node['class']} path={node['path']}")
        if (secondary_files := get_in(self.definition, ['inputs', key, 'secondaryFiles'])):
            print(f"secondary_files={secondary_files}")
        return node

    def _cloudize_node(node, key=None):
        if (node['class'] == 'File'):
            # return self.cloudize_file_node(node, key=key)
            return self._print_file_node(node, key=key)
        else:
            return node

    def cloudize(self):
        self.cloudized_inputs = walk_object(self.inputs, self._cloudize_node)
        # yaml.dump(self.cloudized_inputs, cloudize_file_path(inputs_path))


if __name__ == '__main__':
    Workflow(INPUTS_FILE, DEFINITION_FILE).cloudize()
