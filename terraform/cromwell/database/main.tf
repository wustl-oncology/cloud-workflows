resource google_sql_database_instance "master" {
  name = "cromwell"
  database_version = "MYSQL_5_7"
  region = var.region
  settings {
    tier = var.instance_type
    activation_policy = "ALWAYS"
    disk_autoresize = true
    backup_configuration {
      enabled = true
      binary_log_enabled = true
    }
    ip_configuration {
      ipv4_enabled = true
      dynamic authorized_networks {
        for_each = var.authorized_networks
        iterator = network
        content {
          name = "network-${network.key}"
          value = network.value
        }
      }
    }
    location_preference {
      zone = var.zone
    }
  }
}

resource "google_sql_database" "master" {
  name = "cromwell"
  instance = google_sql_database_instance.master.name
}

resource "google_sql_user" "root" {
  name = "root"
  instance = google_sql_database_instance.master.name
  host = "%"
  password = var.root_password
}
