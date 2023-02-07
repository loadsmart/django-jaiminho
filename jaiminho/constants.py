class PublishStrategyType:
    PUBLISH_ON_COMMIT = "publish-on-commit"
    KEEP_ORDER = "keep-order"

    CHOICES = ((PUBLISH_ON_COMMIT, "Publish on Commit"), (KEEP_ORDER, "Keep Order"))
