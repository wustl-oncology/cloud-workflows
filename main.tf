# --- Variables ----------------------------------------------------------------

locals {
  project    = "griffith-lab"
  project_id = 190642530876  # TODO: pull from provider?
  region = "us-central1"
  zone   = "us-central1-c"
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
  region  = local.region
  zone    = local.zone
}

module "cromwell" {
  source     = "./cromwell"
  project    = local.project
  project_id = local.project_id
  region     = local.region
}
