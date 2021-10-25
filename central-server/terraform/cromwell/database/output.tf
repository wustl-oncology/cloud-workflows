output "ip_address" {
  value = google_sql_database_instance.master.public_ip_address
}
