variable cromwell_db_root_password {
  type = string
  sensitive = true
}

variable cromwell_port {
  type = string
}

variable washu_internet_range {
  type = string
}
variable washu_internet2_range {
  type = string
}

variable cromwell_user_emails {
  type = list(string)
}
variable dependent_lab_service_accounts {
  type = list(string)
}
variable gms_service_account {
  type = string
}
