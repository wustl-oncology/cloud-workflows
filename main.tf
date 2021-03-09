# --- Variables ----------------------------------------------------------------

locals {
  project = "griffith-lab"
  creds-file = "${local.project}-terraform-service-account.json"
  cromwell-service-account = "cromwell-server"
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
  credentials = file(local.creds-file)

  project = local.project
  region  = "us-central1"
  zone    = "us-central1-c"
}

# TODO: make Terraform own this service account, should only need to setup
# then run terraform, not contents
data "google_service_account" "cromwell" {
  account_id = local.cromwell-service-account
  project = local.project
}

resource "google_compute_network" "vpc-network" {
  name = "cromwell-network"
}

resource "google_compute_instance" "cromwell-server" {
  name         = "cromwell-server"
  machine_type = "e2-medium"
  boot_disk {
    initialize_params {
      image = "debian-10-buster-v20210217"
    }
  }

  network_interface {
    network = google_compute_network.vpc-network.id
  }

  # TODO: move into its own file
  # TODO: configure backend with `google.conf`
  # TODO: get a machine template with docker already installed
  # TODO: create custom docker image from Cromwell with config file attached
  #   or otherwise pull config somewhere not manual
  metadata_startup_script = <<EOF
curl -sSL https://get.docker.com/ | sh
docker pull broadinstitute/cromwell:58
docker run -p 8000:8000 broadinstitute/cromwell:58 server
EOF

  service_account {
    email = data.google_service_account.cromwell.email
    scopes = ["cloud-platform"]
  }

  allow_stopping_for_update = true
}

# --- File Storage -------------------------------------------------------------

resource "google_storage_bucket" "cromwell-executions" {
  name = "${local.project}-cromwell"
  location = "US"  # TODO: pull from provider?
  # project, pull from provider

  # additional options we may want:
  # uniform_bucket_level_access, requester_pays, encryption, logging, labels,
  # retention_policy, cors, versioning, lifecycle_rule, storage_class

  # ONLY FOR PLAYGROUND
  # _will_ cause data loss if done in a real environment
  # attempts to delete non-empty bucket will delete its contents instead
  # of failing to apply
  force_destroy = "true"
}

resource "google_storage_bucket_acl" "cromwell-executions" {
  bucket = google_storage_bucket.cromwell-executions.name

  role_entity = [
    "OWNER:project-owners-190642530876",
    "OWNER:project-editors-190642530876",
    "READER:project-viewers-190642530876",
    "WRITER:user-${data.google_service_account.cromwell.email}"
  ]
}
