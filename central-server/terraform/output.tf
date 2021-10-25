output "compute_worker_service_account_email" {
  value = module.cromwell.compute_service_account_email
}

output "cromwell_db_ip" {
  value = module.cromwell.db_ip
}

output "cromwell_vm_service_account_email" {
  value = module.cromwell.server_service_account_email
}

output "vm_static_ip_address" {
  value = module.cromwell.server_ip
}

output "vm_subnetwork" {
  value = module.cromwell.subnetwork
}
