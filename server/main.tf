resource "google_service_account" "cromwell-server" {
  account_id = "cromwell-server"
  project = var.project
  description = "To run Cromwell server as part of PipelinesAPI"
  display_name = "cromwell-server"
}

resource "google_project_iam_binding" "project" {
  project = "griffith-lab"
  role    = "roles/lifesciences.workflowsRunner"
  members = ["serviceAccount:${google_service_account.cromwell-server.email}"]
}

resource "google_compute_instance" "cromwell-server" {
  name = "cromwell-server"

  allow_stopping_for_update = true
  machine_type = "e2-medium"
  metadata_startup_script = file("server_startup.py")
  metadata = {
    enable-oslogin = "TRUE"
    service-file   = file("cromwell.service")
    conf-file      = file("cromwell.conf")
  }
  tags = var.tags

  boot_disk {
    initialize_params {
      image = "debian-10-buster-v20210217"
    }
  }
  network_interface {
    subnetwork = var.subnetwork
    access_config { nat_ip = var.nat_ip }
  }
  service_account {
    email = google_service_account.cromwell-server.email
    scopes = ["cloud-platform"]
  }
}
