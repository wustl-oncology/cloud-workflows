variable "authorized_networks" {
  type = list(string)
}
variable "instance_type" {
  type = string
}
variable "root_password" {
  type = string
  sensitive = true
}

variable "region" {
  type = string
}
variable "zone" {
  type = string
}
