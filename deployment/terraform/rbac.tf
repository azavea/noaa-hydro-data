resource "kubernetes_cluster_role_binding" "viewers" {
  metadata {
    name = "viewers"
  }
  role_ref {
    api_group = "rbac.authorization.k8s.io"
    kind = "ClusterRole"
    name = "view"
  }
  subject {
    api_group = "rbac.authorization.k8s.io"
    kind = "Group"
    name = "viewer"
  }
}

resource "kubernetes_cluster_role_binding" "nodewatcher" {
  metadata {
    name = "nodewatcher"
  }
  role_ref {
    api_group = "rbac.authorization.k8s.io"
    kind = "ClusterRole"
    name = "eks:nodewatcher"
  }
  subject {
    api_group = "rbac.authorization.k8s.io"
    kind = "Group"
    name = "nodewatcher"
  }
}
