variable "project_id" {
  type = string
}

variable "bucket" {
  type = string
  description = "Name of the target storage bucket"
}

variable "acl_role_entity" {
  type = list(string)
  default = []
}

variable "iam_members" {
  type = list(object({
    name = string
    roles = list(string)
  }))
  default = []
}

locals {
  iam_members = flatten([
    for m_key, member in var.iam_members : [
      for r_key, role in member.roles : {
        {
          name = member.name
          role = role
        }
      }
    ]
  ])
}

## both IAM and ACL are required
## failed with permissions issue if either are missing

resource "google_storage_bucket_iam_member" "role_binding" {
  for_each = {
    for iam_member in local.iam_members : "${iam_member.name}/${iam_member.role}" => iam_member
  }
  bucket = var.storage_bucket
  role   = each.value.role
  member = each.value.name
  description = "Non-authoritative permission bindings."
}

resource "google_storage_bucket_acl" "cromwell-executions" {
  bucket = google_storage_bucket.cromwell-executions.name

  role_entity = concat([
    "OWNER:project-owners-${local.project-id}",
    "OWNER:project-editors-${local.project-id}",
    "READER:project-viewers-${local.project-id}"
  ], var.acl_role_entity)
  description = "Legacy permission bindings."
}
