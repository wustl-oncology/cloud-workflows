output "compute_service_account_email" {
  value = google_service_account.compute.email
}

output "db_ip" {
  value = module.database.ip_address
}

output "server_service_account_email" {
  value = google_service_account.server.email
}

output "server_ip" {
  value = module.network.static_ip
}

output "subnetwork" {
  value = module.network.subnetwork
}
