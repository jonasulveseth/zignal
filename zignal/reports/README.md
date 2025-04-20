# Zignal Reports Module

This module implements a comprehensive report generation system for the Zignal platform.

## Overview

The Reports module allows users to:
- Create and manage report templates with custom placeholders
- Generate reports from templates using AI
- Schedule recurring report generation
- Export reports as PDFs
- Receive notifications about report completion or failures

## Key Components

### Models

- **ReportTemplate**: Templates for generating reports with placeholders for dynamic content
- **Report**: Generated reports with content, associated with projects or companies
- **ReportSchedule**: Schedules for automatic report generation

### Services

- **ReportGenerationService**: Generates report content using OpenAI based on templates and data
- **DocumentValidationService**: Validates documents against requirements for reports
- **NotificationService**: Sends notifications about report completion or failures

### Views

- Report CRUD operations
- Template management
- Schedule management
- Generation and export functionality

## Usage

1. Create a report template with placeholders for dynamic content
2. Create a report by selecting a template and providing parameters
3. Generate the report using AI
4. View, export, or share the generated report

## Document Validation

Reports can specify document requirements using special comments in templates:
```
<!-- REQUIRE: {"type": "financial_data", "period": "quarterly"} -->
```

The system will validate that required documents are available before generating reports.

## AI Response Generation

Report content is generated using OpenAI, transforming templates and data into comprehensive reports. The system:
1. Gathers data from various sources (projects, companies, data silos)
2. Builds a prompt based on the template and data
3. Uses OpenAI to generate professional report content

## Notifications

The system sends notifications when:
- Reports are successfully generated
- Report generation fails

## Scheduling

Reports can be scheduled to run:
- Daily
- Weekly (on specific days)
- Monthly (on specific days)
- Quarterly

## Future Enhancements

Potential improvements:
- More advanced document validation
- Custom report themes and formatting
- Interactive charts and visualizations
- Collaborative editing features 