"""
Service for validating documents against requirements for reports
"""
import logging
import re
from typing import Dict, List, Any, Tuple, Optional

from django.conf import settings
from openai import OpenAI

from reports.models import Report

logger = logging.getLogger(__name__)

class DocumentValidationService:
    """
    Service for validating documents against requirements for reports
    """
    
    def __init__(self):
        self.client = OpenAI(api_key=settings.OPENAI_API_KEY)
        self.default_model = settings.OPENAI_MODEL
    
    def validate_documents(self, report: Report) -> Tuple[bool, Dict[str, Any]]:
        """
        Validate the documents against the requirements for the report
        
        Args:
            report: The report to validate documents for
            
        Returns:
            Tuple[bool, Dict[str, Any]]: (is_valid, validation_results)
        """
        try:
            # Get documents related to the report (from project or company data silos)
            documents = self._get_related_documents(report)
            
            if not documents:
                return False, {"error": "No documents found to validate"}
            
            # Extract requirements from the report template
            requirements = self._extract_requirements(report)
            
            if not requirements:
                return True, {"message": "No specific requirements to validate against"}
            
            # Validate each document against requirements
            validation_results = {}
            all_valid = True
            
            for doc_id, document in documents.items():
                doc_result = self._validate_document(document, requirements)
                validation_results[doc_id] = doc_result
                
                if not doc_result["is_valid"]:
                    all_valid = False
            
            return all_valid, {
                "overall_valid": all_valid,
                "document_results": validation_results,
                "requirements": requirements
            }
            
        except Exception as e:
            logger.error(f"Error validating documents for report {report.id}: {str(e)}")
            return False, {"error": str(e)}
    
    def _get_related_documents(self, report: Report) -> Dict[str, Any]:
        """
        Get documents related to the report from project or company data silos
        
        Args:
            report: The report to get documents for
            
        Returns:
            Dict[str, Any]: Dictionary of document IDs to document content
        """
        documents = {}
        
        # If report is associated with a project, get documents from project data silos
        if report.project:
            from datasilo.models import DataSilo, DataFile
            
            # Get data silos associated with the project
            silos = DataSilo.objects.filter(project=report.project)
            
            # Get files from these silos
            for silo in silos:
                files = DataFile.objects.filter(data_silo=silo)
                
                for file in files:
                    # Only consider text-based files
                    if file.file_type in ['document', 'spreadsheet', 'code']:
                        # In a real implementation, we would extract and process the text
                        # For now, just use the file name and description as placeholder
                        documents[f"file_{file.id}"] = {
                            "name": file.name,
                            "description": file.description,
                            "type": file.file_type,
                            "content": "Sample content from the file"  # Placeholder
                        }
        
        # Similarly for company-associated reports
        if report.company:
            from datasilo.models import DataSilo, DataFile
            
            silos = DataSilo.objects.filter(company=report.company)
            
            for silo in silos:
                files = DataFile.objects.filter(data_silo=silo)
                
                for file in files:
                    if file.file_type in ['document', 'spreadsheet', 'code']:
                        documents[f"file_{file.id}"] = {
                            "name": file.name,
                            "description": file.description,
                            "type": file.file_type,
                            "content": "Sample content from the file"  # Placeholder
                        }
        
        return documents
    
    def _extract_requirements(self, report: Report) -> List[Dict[str, Any]]:
        """
        Extract requirements from the report template
        
        Args:
            report: The report to extract requirements for
            
        Returns:
            List[Dict[str, Any]]: List of requirements
        """
        requirements = []
        
        # Get template
        template = report.template
        if not template or not template.template_content:
            return requirements
        
        # Look for requirement blocks in the template
        # Example format: <!-- REQUIRE: {"type": "financial_data", "period": "quarterly"} -->
        regex = r"<!--\s*REQUIRE:\s*({.*?})\s*-->"
        matches = re.findall(regex, template.template_content)
        
        import json
        for match in matches:
            try:
                req = json.loads(match)
                requirements.append(req)
            except json.JSONDecodeError:
                logger.warning(f"Invalid requirement format in template: {match}")
        
        return requirements
    
    def _validate_document(self, document: Dict[str, Any], requirements: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Validate a document against requirements using AI
        
        Args:
            document: The document to validate
            requirements: The requirements to validate against
            
        Returns:
            Dict[str, Any]: Validation results
        """
        # In a real implementation, this would use more sophisticated validation
        # including NLP/AI to check if document contents match requirements
        
        # For now, use OpenAI to evaluate if the document meets the requirements
        try:
            # Prepare prompt
            prompt = f"""
Please evaluate if the following document meets these requirements:

Document:
Name: {document.get('name')}
Description: {document.get('description')}
Content: {document.get('content')}

Requirements:
{requirements}

Your task:
1. Analyze if the document contains the information needed to satisfy each requirement
2. Provide a "yes" or "no" answer for each requirement
3. Explain your reasoning

Format your response as a JSON object with:
- overall_valid: true/false
- requirement_results: [list of results for each requirement]
- explanation: your overall explanation
"""
            
            # For demonstration purposes, we'll return a mock result instead of calling OpenAI
            # In a real implementation, you would call the API here
            mock_result = {
                "is_valid": True,
                "requirement_results": [
                    {
                        "requirement": req,
                        "is_met": True,
                        "explanation": f"The document contains information related to {req.get('type', 'unknown')}"
                    }
                    for req in requirements
                ],
                "explanation": "The document meets all the specified requirements."
            }
            
            return mock_result
            
        except Exception as e:
            logger.error(f"Error validating document {document.get('name')}: {str(e)}")
            return {
                "is_valid": False,
                "error": str(e)
            } 