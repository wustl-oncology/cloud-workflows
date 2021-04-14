resource "google_compute_subnetwork" "default" {
  name = "cromwell"
  ip_cidr_range = "10.10.0.0/16"
  network = var.network_id
}

resource "google_compute_address" "static_ip" {
  name = "cromwell-server-ip"
  network_tier = "PREMIUM"
  address_type = "EXTERNAL"
}

resource "google_compute_firewall" "default_ssh_allowed" {
  name = "default-ssh-allowed"
  network = var.network_id
  allow {
    # what do we need icmp for? monitoring?
    protocol = "icmp"
  }
  allow {  # allow SSH
    protocol = "tcp"
    ports = ["22", var.cromwell_port]
  }
  source_ranges = ["0.0.0.0/0"]  # all IPs allowed
  target_tags = [var.ssh_tag]
}
