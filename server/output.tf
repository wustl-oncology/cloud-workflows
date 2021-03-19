output "service_account_name" {
  value = google_service_account.cromwell_server.name
}

output "service_account_email" {
  value = google_service_account.cromwell_server.email
}
