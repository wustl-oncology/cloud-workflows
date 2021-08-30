variable "project" {
  type = string
}
variable "project_id" {
  type = string
}

variable "user_emails" {
  type = list(string)
}

variable "dependent_lab_service_accounts" {
  type = list(string)
}

variable "compute_account_email" {
  type = string
}
variable "server_account_email" {
  type = string
}
