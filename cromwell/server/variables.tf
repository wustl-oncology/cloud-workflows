variable "bucket" {
  type = string
  description = <<EOF
name of thegoogle_storage_bucket that Cromwell will use for file storage
EOF
}
variable "cromwell_port" {
  type = number
}
variable "nat_ip" {
  type = string
}
variable "project" {
  type = string
}
variable "region" {
  type = string
}
variable "compute_account_email" {
  type = string
  description = "email of service account for compute nodes to use"
}
variable "server_account_email" {
  type = string
  description = "email of service account for Cromwell server to use"
}
variable "subnetwork" {
  type = string
  description = "google_compute_subnetwork name"
}
variable "tags" {
  type = list(string)
  default = []
}
