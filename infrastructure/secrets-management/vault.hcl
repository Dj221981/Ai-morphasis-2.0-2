storage "file" {
  path = "/vault/data"
}

listener "tcp" {
  # Production-safe baseline: replace certificate paths with managed cert material.
  address     = "127.0.0.1:8200"
  tls_disable = false
  tls_cert_file = "/vault/tls/tls.crt"
  tls_key_file  = "/vault/tls/tls.key"
}

ui = true
