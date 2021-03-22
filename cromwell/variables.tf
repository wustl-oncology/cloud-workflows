variable "project" {
  type = string
}
variable "project_id" {
  type = number
}

variable "region" {
  type = string
}

variable "ssh_allowed_tag" {
  type = string
  default = "cromwell-ssh-allowed"
  description = <<EOF
tag name to use to indicate SSH is allowed on a VM compute
node. This value is used a firewall setting and should not collide with
existing behavior in a project. Override if, for some reason, cromwell-ssh-allowed
is being used for some other behavior.
EOF
}
