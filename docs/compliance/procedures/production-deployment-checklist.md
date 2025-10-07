# Production Deployment Checklist

This checklist must be completed for all deployments to the production environment. The purpose of this checklist is to ensure that all changes are deployed in a safe and controlled manner, in order to minimize the risk of service disruptions and security vulnerabilities.

## Pre-Deployment

-   [ ] All code changes have been peer-reviewed and approved.
-   [ ] All automated tests have passed in the staging environment.
-   [ ] A rollback plan has been created and documented.
-   [ ] The change has been approved by all required stakeholders.
-   [ ] The change has been documented in the [Change Log](../evidence-templates/change-log.csv).

## Deployment

-   [ ] The deployment has been scheduled during a low-traffic period.
-   [ ] The deployment is being monitored by the on-call engineer.
-   [ ] The deployment is being performed using an automated deployment script.

## Post-Deployment

-   [ ] The application is up and running in the production environment.
-   [ ] The application is passing all health checks.
-   [ ] The on-call engineer has verified that the change is working as expected.
-   [ ] The deployment has been marked as complete in the [Change Log](../evidence-templates/change-log.csv).


