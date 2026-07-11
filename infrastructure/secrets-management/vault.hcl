storage "file" {
  path = "/vault/data"
}

listener "tcp" {
  # Local development template only. Use TLS and restricted interfaces in shared environments.
  address     = "127.0.0.1:8200"
  tls_disable = 1
}

ui = true
