# Brikk Infrastructure Documentation

## Getting Started with Compliance

This documentation provides a comprehensive framework for HIPAA and SOC 2 compliance readiness. Start here to understand how to implement and maintain compliance at Brikk.

### Quick Start Guide

1. **Begin with Policies**: Review and customize the [compliance policies](./compliance/policies/) to match your organization's specific requirements. These high-level documents require management approval and form the foundation of your compliance program.

2. **Implement Procedures**: Use the [compliance procedures](./compliance/procedures/) as actionable checklists for daily operations. These translate policy requirements into specific workflows.

3. **Start Evidence Collection**: Use the [evidence templates](./compliance/evidence-templates/) to begin documenting compliance activities. These CSV files can be imported into spreadsheet applications or compliance management tools.

4. **Map Your Controls**: Review the [controls matrix](./compliance/controls-matrix.md) to understand how existing technical implementations support compliance requirements.

### Using Evidence Templates

The evidence templates are designed for immediate use:

- **Risk Register**: Track and manage identified security risks
- **Access Review Log**: Document periodic reviews of user access rights  
- **Incident Log**: Record and track security incidents
- **Change Log**: Document all changes to production systems

Each template includes sample data to demonstrate proper completion. Simply replace the examples with your actual data and maintain the files as ongoing compliance evidence.

### Documentation Structure

```
docs/
├── README.md (this file)
└── compliance/
    ├── README.md (compliance overview)
    ├── policies/ (high-level governance documents)
    ├── procedures/ (actionable workflows)
    ├── evidence-templates/ (CSV templates for tracking)
    └── controls-matrix.md (technical controls mapping)
```

### Next Steps

After implementing the starter pack:

1. **Customize for Your Environment**: Adapt policies and procedures to your specific technology stack and business processes
2. **Integrate with Tools**: Consider integrating evidence templates with compliance management platforms
3. **Regular Reviews**: Establish quarterly reviews of policies and procedures to ensure they remain current
4. **Audit Preparation**: Use the framework to prepare for formal compliance audits

For questions about specific compliance requirements or implementation guidance, consult with your legal and security teams.


## Continuous Integration (CI) and Security

Our CI pipeline includes automated security checks to ensure the integrity and security of our codebase. For a detailed breakdown of these checks, see the **CI Truth Table** in our [SECURITY_CI.md](./SECURITY_CI.md#ci-truth-table) documentation.

### Evidence Locations

- **CI Run Logs**: Detailed logs for each CI run are available in the **Actions** tab of the GitHub repository.
- **Test Artifacts**: Test reports and other artifacts are available for download from the summary page of each CI run.

