package medviet.data_access

import future.keywords.if
import future.keywords.in

default allow := false
default deny := false

# Admin can access everything except explicitly denied actions.
allow if {
    not deny
    input.user.role == "admin"
}

# ML engineers can work with training data and model artifacts.
allow if {
    not deny
    input.user.role == "ml_engineer"
    input.resource in {"training_data", "model_artifacts"}
    input.action in {"read", "write"}
}

# ML engineers cannot delete production data.
deny if {
    input.user.role == "ml_engineer"
    input.resource == "production_data"
    input.action == "delete"
}

# Data analysts can read aggregated metrics.
allow if {
    not deny
    input.user.role == "data_analyst"
    input.resource == "aggregated_metrics"
    input.action == "read"
}

# Data analysts can write reports.
allow if {
    not deny
    input.user.role == "data_analyst"
    input.resource == "reports"
    input.action == "write"
}

# Interns can only access sandbox data.
allow if {
    not deny
    input.user.role == "intern"
    input.resource == "sandbox_data"
    input.action in {"read", "write"}
}

# Restricted data cannot be exported outside VN servers.
deny if {
    input.data_classification == "restricted"
    input.destination_country != "VN"
}
