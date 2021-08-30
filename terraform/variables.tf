variable cromwell_db_root_password {
  type = string
  sensitive = true
}

variable cromwell_port {
  type = string
}

variable washu_vpn_range {
  type = string
}

variable dependent_lab_service_accounts {
  type = list(string)
}
