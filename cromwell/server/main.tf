resource "google_compute_instance" "cromwell_server" {
  name = "cromwell-server"

  allow_stopping_for_update = true
  machine_type = "e2-medium"
  metadata_startup_script = file("cromwell/server_startup.py")
  metadata = {
    enable-oslogin = "TRUE"
    service-file   = file("cromwell/cromwell.service")
    conf-file      = <<EOF
${file("cromwell/cromwell.conf")}
webservice.port = ${var.cromwell_port}
engine.filesystems.gcs.project = ${var.project}

backend.providers.PAPIv2.config {
  project = ${var.project}
  root = "gs://${var.bucket}/cromwell-execution"

  genomics {
    compute-service-account = ${var.compute_account_email}
    location =  ${var.region}
  }
  filesystems.gcs.project = ${var.project}
}
EOF
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
    email = var.server_account_email
    scopes = ["cloud-platform"]
  }
}
