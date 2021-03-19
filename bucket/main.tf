locals {
  bucket_roles = ["roles/storage.objectCreator", "roles/storage.objectViewer"]
  iam_members = flatten([
    for m_key, account in var.writer_service_accounts : [
      for r_key, role in toset(local.bucket_roles) : {
        {
          name = account
          role = role
        }
      }
    ]
  ])
}

resource "google_storage_bucket" "cromwell-executions" {
  name = "${var.project}-cromwell"
  location = "US"  # TODO: pull from provider?
}

## both IAM and ACL are required
## failed with permissions issue if either are missing

resource "google_storage_bucket_iam_member" "role_binding" {
  for_each = {
    for iam_member in local.iam_members : "${iam_member.name}/${iam_member.role}" => iam_member
  }
  bucket = google_storage_bucket.cromwell-executions.name
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
  ], [for account in var.writer-service-accounts : "WRITER:user-${account}"])
  description = "Legacy permission bindings."
}
