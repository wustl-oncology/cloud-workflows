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
  members = concat([
    "serviceAccount:${google_service_account.compute.email}"
  ], formatlist("serviceAccount:%s", var.dependent_lab_service_accounts))
}

# ---- Modules ---------------------------------------------------------

module "network" {
  source  = "./network"
  target_tag    = var.target_network_tag
  cromwell_port = var.cromwell_port
  network_id    = var.network_id
  source_ranges = var.allowed_ip_ranges
}

module "bucket" {
  source  = "./bucket"
  project = var.project
  project_id = var.project_id
  user_emails = var.user_emails
  dependent_lab_service_accounts = var.dependent_lab_service_accounts
  compute_account_email = google_service_account.compute.email
  server_account_email  = google_service_account.server.email
}

module "database" {
  source = "./database"
  region = var.region
  zone = var.zone
  root_password = var.db_root_password
  instance_type = var.db_instance_type
  authorized_networks = ["${module.network.static_ip}/32"]
}
