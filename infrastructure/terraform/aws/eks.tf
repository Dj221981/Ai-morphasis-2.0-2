resource "aws_eks_cluster" "this" {
  name     = "${var.project_name}-${var.environment}-eks"
  role_arn = aws_iam_role.eks_cluster.arn

  vpc_config {
    subnet_ids = [aws_subnet.private_a.id]
  }

  depends_on = [aws_iam_role_policy_attachment.eks_cluster]
}
