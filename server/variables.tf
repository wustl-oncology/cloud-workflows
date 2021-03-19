variable "project" {
  type = string
}
variable "conf_file" {
  type = string
}
variable "nat_ip" {
  type = string
}
variable "service_file" {
  type = string
}
variable "startup_script" {
  type = string
}
variable "subnetwork" {
  type = string
  description = "google_compute_subnetwork name"
}
variable "tags" {
  type = list(string)
}
