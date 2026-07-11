resource "aws_ecr_repository" "app" {
  name                 = "${var.project_name}/app"
  image_tag_mutability = "IMMUTABLE"
}

resource "aws_ecr_repository" "trainer" {
  name                 = "${var.project_name}/trainer"
  image_tag_mutability = "IMMUTABLE"
}
