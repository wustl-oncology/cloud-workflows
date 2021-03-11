# --- Variables ----------------------------------------------------------------

locals {
  project = "griffith-lab"
  project-id = 190642530876  # TODO: pull from provider?
}

# ------------------------------------------------------------------------------

terraform {
  required_providers {
    google = {
      source = "hashicorp/google"
      version = "3.5.0"
    }
  }
}

provider "google" {
  // if this file gets expanded to other labs, these should be tfvars
  credentials = file("terraform-service-account.json")

  project = local.project
  region  = "us-central1"
  zone    = "us-central1-c"
}

# --- Cromwell Server ---------------------------------------------------------

resource "google_service_account" "cromwell-server" {
  account_id = "cromwell-server"
  project = local.project
  description = "To run Cromwell server as part of PipelinesAPI"
  display_name = "cromwell-server"
}

resource "google_project_iam_binding" "project" {
  project = "griffith-lab"
  role    = "roles/lifesciences.workflowsRunner"

  members = [
    "serviceAccount:${google_service_account.cromwell-server.email}",
  ]
}

resource "google_compute_instance" "cromwell-server" {
  name = "cromwell-server"

  allow_stopping_for_update = true
  machine_type = "e2-medium"
  # TODO: after google.conf configured, fix .sh to actually run a Cromwell server
  metadata_startup_script = file("cromwell_server_startup.sh")
  tags = ["http-server", "https-server"]

  boot_disk {
    initialize_params {
      image = "debian-10-buster-v20210217"
    }
  }
  network_interface {
    network = "default"
  }
  service_account {
    email = google_service_account.cromwell-server.email
    scopes = ["cloud-platform"]
  }
}

# --- Cromwell Compute ---------------------------------------------------------

resource "google_service_account" "cromwell-compute" {
  account_id = "cromwell-compute"
  display_name = "Cromwell backend compute"
  description = <<EOF
Service account for compute resources spun up by Cromwell server.
Per Cromwell's docs, must be a service account user of the cromwell-server
service account and have read/write access to the cromwell-execution bucket.
EOF
}

resource "google_service_account_iam_binding" "cromwell-service-account-user" {
  service_account_id = google_service_account.cromwell-server.name
  role = "roles/iam.serviceAccountUser"
  members = [
    "serviceAccount:${google_service_account.cromwell-compute.email}"
  ]
}

# --- File Storage -------------------------------------------------------------

resource "google_storage_bucket" "cromwell-executions" {
  name = "${local.project}-cromwell"
  location = "US"  # TODO: pull from provider?

  # additional options we may want:
  # uniform_bucket_level_access, requester_pays, encryption, logging, labels,
  # retention_policy, cors, versioning, lifecycle_rule, storage_class

  # ONLY FOR PLAYGROUND
  # _will_ cause data loss if done in a real environment
  # attempts to delete non-empty bucket will delete its contents instead
  # of failing to apply
  force_destroy = "true"
}

## both IAM and ACL are required
## failed with permissions issue if either are missing

resource "google_storage_bucket_iam_member" "cromwell-server" {
  for_each = toset(["roles/storage.objectCreator", "roles/storage.objectViewer"])
  bucket   = google_storage_bucket.cromwell-executions.name
  role     = each.key
  member   = "serviceAccount:${google_service_account.cromwell-server.email}"
}
resource "google_storage_bucket_iam_member" "cromwell-compute" {
  for_each = toset(["roles/storage.objectCreator", "roles/storage.objectViewer"])
  bucket   = google_storage_bucket.cromwell-executions.name
  role     = each.key
  member   = "serviceAccount:${google_service_account.cromwell-compute.email}"
}

resource "google_storage_bucket_acl" "cromwell-executions" {
  bucket = google_storage_bucket.cromwell-executions.name

  role_entity = [
    "OWNER:project-owners-${local.project-id}",
    "OWNER:project-editors-${local.project-id}",
    "READER:project-viewers-${local.project-id}",
    "WRITER:user-${google_service_account.cromwell-server.email}",
    "WRITER:user-${google_service_account.cromwell-compute.email}"
  ]
}

# --- Networking ---------------------------------------------------------------

# --- Database -----------------------------------------------------------------
