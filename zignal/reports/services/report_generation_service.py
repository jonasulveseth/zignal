"""
Service for AI-based report generation
"""
import logging
import json
from datetime import datetime
from typing import Dict, Any, Optional

from django.conf import settings
from openai import OpenAI

from reports.models import Report, ReportTemplate
from reports.services.document_validation_service import DocumentValidationService
from reports.services.notification_service import ReportNotificationService

logger = logging.getLogger(__name__)

class ReportGenerationService:
    """
    Service for generating reports using AI
    """
    
    def __init__(self):
        self.client = OpenAI(api_key=settings.OPENAI_API_KEY)
        self.default_model = settings.OPENAI_MODEL
        self.validation_service = DocumentValidationService()
        self.notification_service = ReportNotificationService()
    
    def generate_report(self, report: Report) -> bool:
        """
        Generate a report using OpenAI based on the template and parameters
        
        Args:
            report: The Report object to generate content for
            
        Returns:
            bool: True if generation was successful, False otherwise
        """
        try:
            # Update report status
            report.status = 'generating'
            report.save()
            
            # Get template
            template = report.template
            if not template:
                raise ValueError("Report must have a template")
            
            # Validate documents against requirements if enabled
            if getattr(settings, 'VALIDATE_DOCUMENTS_FOR_REPORTS', False):
                is_valid, validation_results = self.validation_service.validate_documents(report)
                
                if not is_valid:
                    error_message = validation_results.get('error', 'Document validation failed')
                    logger.warning(f"Document validation failed for report {report.id}: {error_message}")
                    
                    # We proceed anyway, but store validation results in report parameters
                    if 'validation_results' not in report.parameters:
                        report.parameters['validation_results'] = {}
                    
                    report.parameters['validation_results'] = validation_results
                    report.save()
            
            # Gather data needed for the report
            report_data = self._gather_report_data(report)
            
            # Build the prompt
            prompt = self._build_prompt(template.template_content, report_data)
            
            # Generate content using OpenAI
            response = self.client.chat.completions.create(
                model=self.default_model,
                messages=[
                    {"role": "system", "content": "You are a professional report generation assistant. Your task is to produce comprehensive, well-structured reports based on provided data and template instructions."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,  # Lower temperature for more consistent, factual reports
                max_tokens=4000
            )
            
            # Extract generated content
            content = response.choices[0].message.content
            
            # Update report with generated content
            report.content = content
            report.status = 'generated'
            report.generated_at = datetime.now()
            report.save()
            
            # Generate PDF if needed
            if getattr(settings, 'AUTO_GENERATE_REPORT_PDF', False):
                self._generate_pdf(report)
            
            # Send notifications
            self.notification_service.notify_report_completion(report)
            
            return True
            
        except Exception as e:
            logger.error(f"Error generating report {report.id}: {str(e)}")
            report.status = 'failed'
            report.save()
            
            # Send failure notifications
            self.notification_service.notify_report_failure(report, str(e))
            
            return False
    
    def _gather_report_data(self, report: Report) -> Dict[str, Any]:
        """
        Gather all data needed for the report
        
        Args:
            report: The Report object
            
        Returns:
            dict: Data to be used in the report
        """
        data = {
            "report_info": {
                "title": report.title,
                "description": report.description,
                "created_at": report.created_at.isoformat(),
                "created_by": str(report.created_by) if report.created_by else None,
            },
            "parameters": report.parameters
        }
        
        # Add project data if applicable
        if report.project:
            data["project"] = {
                "name": report.project.name,
                "description": report.project.description,
                # Add more project data as needed
            }
        
        # Add company data if applicable
        if report.company:
            data["company"] = {
                "name": report.company.name,
                # Add more company data as needed
            }
        
        # Here we would add more data sources as needed:
        # - Data from connected data silos
        # - Financial data
        # - Performance metrics
        # - etc.
        
        return data
    
    def _build_prompt(self, template_content: str, data: Dict[str, Any]) -> str:
        """
        Build the prompt for the OpenAI API based on the template and data
        
        Args:
            template_content: The template content with placeholders
            data: Data to be used in the report
            
        Returns:
            str: The prompt for the OpenAI API
        """
        prompt = f"""
Generate a professional report based on the following template and data.

# TEMPLATE:
{template_content}

# DATA:
{json.dumps(data, indent=2)}

# INSTRUCTIONS:
1. Follow the template structure exactly, replacing placeholders with actual data.
2. Generate professional, factual content based on the provided data.
3. Format the report with proper headings, subheadings, and paragraphs.
4. Include visualizations instructions where appropriate (describe what charts/graphs would be included).
5. Use a professional business tone.
6. The length should be appropriate for the content, typically 1000-2000 words.

Please generate the complete report content now:
"""
        return prompt
    
    def _generate_pdf(self, report: Report) -> Optional[str]:
        """
        Generate a PDF for the report
        
        Args:
            report: The Report object
            
        Returns:
            Optional[str]: Path to the generated PDF or None if generation failed
        """
        # Placeholder for PDF generation logic
        # This would typically use a library like WeasyPrint or a service like wkhtmltopdf
        # For now, we'll just log that it would be generated
        logger.info(f"PDF generation for report {report.id} would happen here")
        return None 