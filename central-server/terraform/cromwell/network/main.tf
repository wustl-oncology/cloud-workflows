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

resource "google_compute_firewall" "cromwell_firewall" {
  name = "cromwell-firewall"
  network = var.network_id
  allow {
    # what do we need icmp for? monitoring?
    protocol = "icmp"
  }
  allow {  # allow SSH
    protocol = "tcp"
    ports = ["22"]
  }
  allow {  # http, https
    protocol = "tcp"
    ports = [var.cromwell_port, "80", "443"]
  }
  source_ranges = var.source_ranges
  target_tags = [var.target_tag]
}
