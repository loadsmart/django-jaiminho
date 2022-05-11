module "circleci" {
  source             = "git@github.com:loadsmart/terraform-modules.git//circleci-app"
  project            = "jaiminho"
  allow_publish_docs = true
}
