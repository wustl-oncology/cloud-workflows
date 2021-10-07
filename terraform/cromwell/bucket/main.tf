locals {
  bucket_roles = ["roles/storage.objectCreator", "roles/storage.objectViewer"]
  bucket_writers = [var.server_account_email, var.compute_account_email]
}

resource "google_storage_bucket" "cromwell_executions" {
  name = "${var.project}-cromwell"
  location = "US"  # TODO: pull from provider?
  force_destroy = true
}

## both IAM and ACL are required
## failed with permissions issue if either are missing

# non-authoritative IAM bindings
resource "google_storage_bucket_iam_member" "server_binding" {
  for_each = toset(local.bucket_roles)
  bucket = google_storage_bucket.cromwell_executions.name
  role   = each.key
  member = "serviceAccount:${var.server_account_email}"
}
resource "google_storage_bucket_iam_member" "compute_binding" {
  for_each = toset(local.bucket_roles)
  bucket = google_storage_bucket.cromwell_executions.name
  role   = each.key
  member = "serviceAccount:${var.compute_account_email}"
}

resource "google_storage_bucket_iam_member" "user_read_access" {
  for_each = toset(var.user_emails)
  bucket   = google_storage_bucket.cromwell_executions.name
  role     = "roles/storage.objectViewer"
  member   = "user:${each.key}"
}

resource "google_storage_bucket_iam_member" "service_account_read_access" {
  for_each = toset(concat(var.reader_service_accounts, var.writer_service_accounts))
  bucket   = google_storage_bucket.cromwell_executions.name
  role     = "roles/storage.objectViewer"
  member   = "serviceAccount:${each.key}"
}
resource "google_storage_bucket_iam_member" "service_account_write_access" {
  for_each = toset(var.writer_service_accounts)
  bucket   = google_storage_bucket.cromwell_executions.name
  role     = "roles/storage.objectCreator"
  member   = "serviceAccount:${each.key}"
}

# Legacy permission bindings
resource "google_storage_bucket_acl" "cromwell_executions" {
  bucket = google_storage_bucket.cromwell_executions.name
  role_entity = [
    "OWNER:project-owners-${var.project_id}",
    "READER:project-viewers-${var.project_id}",
    "OWNER:project-editors-${var.project_id}",
    "WRITER:user-${var.server_account_email}",
    "WRITER:user-${var.compute_account_email}"
  ]
}
