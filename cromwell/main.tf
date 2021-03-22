locals {
  # should match webservice.port in cromwell.conf
  cromwell_port = 8000
}

# ---- Server service account ------------------------------------------

resource "google_service_account" "server" {
  account_id = "cromwell-server"
  project = var.project
  description = "To run Cromwell server as part of PipelinesAPI"
  display_name = "cromwell-server"
}
resource "google_project_iam_binding" "project" {
  project = "griffith-lab"
  role    = "roles/lifesciences.workflowsRunner"
  members = ["serviceAccount:${google_service_account.server.email}"]
}

# ---- Compute service account -----------------------------------------

resource "google_service_account" "compute" {
  account_id = "cromwell-compute"
  display_name = "Cromwell backend compute"
  description = <<EOF
Service account for compute resources spun up by Cromwell server.
Per Cromwell's docs, must be a service account user of the cromwell-server
service account and have read/write access to the cromwell-execution bucket.
EOF
}

resource "google_service_account_iam_binding" "compute_use_server" {
  service_account_id = google_service_account.server.name
  role = "roles/iam.serviceAccountUser"
  members = [
    "serviceAccount:${google_service_account.compute.email}"
  ]
}

# ---- Modules ---------------------------------------------------------

module "network" {
  source  = "./network"
  ssh_tag = var.ssh_allowed_tag
  cromwell_port = local.cromwell_port
}

module "bucket" {
  source  = "./bucket"
  project = var.project
  project_id = var.project_id
  compute_account_email = google_service_account.compute.email
  server_account_email  = google_service_account.server.email
}

module "server" {
  source  = "./server"
  project = var.project
  region  = var.region
  bucket  = module.bucket.name
  # service accounts
  compute_account_email = google_service_account.compute.email
  server_account_email  = google_service_account.server.email
  # network
  nat_ip     = module.network.static_ip
  subnetwork = module.network.subnetwork
  cromwell_port = local.cromwell_port

  tags = ["http-server", "https-server", var.ssh_allowed_tag]
}
