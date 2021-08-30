variable "project" {
  type = string
}
variable "project_id" {
  type = number
}
variable "region" {
  type = string
}
variable "zone" {
  type = string
}

variable "cromwell_port" {
  type = string
}

variable "dependent_lab_service_accounts" {
  type = list(string)
}

# ---- Database --------------------------------------------------------

variable "db_instance_type" {
  type = string
}

variable "db_root_password" {
  type = string
  sensitive = true
}

variable "network_id" {
  type = string
  description = "ID of the Network to create subnetwork, static IP, etc"
}

variable "allowed_ip_ranges" {
  type = list(string)
}

variable "target_network_tag" {
  type = string
  default = "cromwell-server"
}
