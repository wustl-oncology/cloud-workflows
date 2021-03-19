resource "google_compute_network" "default" {
  name                    = "cromwell-default"
  auto_create_subnetworks = false
}

# what do we need subnetwork for?
resource "google_compute_subnetwork" "default" {
  name = "cromwell-default"
  ip_cidr_range = "10.10.0.0/16"
  network = google_compute_network.default.id
}

resource "google_compute_address" "static-ip" {
  name = "cromwell-server-ip"
  network_tier = "PREMIUM"
}

resource "google_compute_firewall" "default-ssh-allowed" {
  name = "default-ssh-allowed"
  network = google_compute_network.default.id
  allow {
    # what do we need icmp for? monitoring?
    protocol = "icmp"
  }
  allow {  # allow SSH
    protocol = "tcp"
    ports = ["22", local.cromwell-port]
  }
  source_ranges = ["0.0.0.0/0"]  # all IPs allowed
  target_tags = [var.ssh_tag]
}
