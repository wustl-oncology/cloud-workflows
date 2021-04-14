locals {
  project    = "griffith-lab"
  project_id = 190642530876  # TODO: pull from provider?
  region = "us-central1"
  zone   = "us-central1-c"
}

terraform {
  required_providers {
    google = {
      source = "hashicorp/google"
      version = "3.5.0"
    }
  }
  backend "gcs" {
    bucket  = "griffith-lab-terraform-state"
    prefix  = "cloud-workflows"
  }
}

provider "google" {
  credentials = file("terraform-service-account.json")

  project = local.project
  region  = local.region
  zone    = local.zone
}

resource "google_compute_network" "custom-default" {
  name = "${local.project}-default"
  auto_create_subnetworks = false
}

module "cromwell" {
  source     = "./cromwell"
  project    = local.project
  project_id = local.project_id
  region     = local.region
  zone       = local.zone

  network_id = google_compute_network.custom-default.id

  db_instance_type = "db-n1-standard-2"
  db_root_password = var.cromwell_db_root_password
}
