output "static_ip" {
  value = google_compute_address.static_ip.address
}

output "subnetwork" {
  value = google_compute_subnetwork.default.name
}
