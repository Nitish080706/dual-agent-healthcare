import os
import json
from typing import Dict, List, Any
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()


class VisualizationAgent:
    """
    Agent responsible for structuring and normalizing medical lab data
    for visualization in charts and graphs.
    """
    
    def __init__(self):
        # Use analysis API key for visualization processing
        groq_api_key = os.getenv("GROQ_ANALYSIS_API_KEY")
        if not groq_api_key:
            raise ValueError("GROQ_ANALYSIS_API_KEY is required for Visualization Agent")
        
        self.client = OpenAI(
            api_key=groq_api_key,
            base_url="https://api.groq.com/openai/v1"
        )
        self.model = "llama-3.3-70b-versatile"
    
    def structure_patient_chart_data(self, structured_data: dict, 
                                    analysis_result: dict) -> dict:
        """
        Structure data for patient-facing visualizations.
        
        Args:
            structured_data: Raw lab values from Extractor
            analysis_result: Medical analysis results
            
        Returns:
            Dictionary with structured chart data for patient view
        """
        print("   Structuring Patient Chart Data (Visualization Agent)...")
        
        lab_results = structured_data.get("lab_results", [])
        overall_health = analysis_result.get("health_summary", {}).get("overall_health_reading", "Unknown")
        abnormalities = analysis_result.get("detailed_analysis", {}).get("abnormalities", [])
        
        # Map health status to numeric score
        health_score_map = {
            'Excellent': 100,
            'Good': 75,
            'Moderate': 50,
            'Danger': 25,
            'Unknown': 0
        }
        
        current_health_score = health_score_map.get(overall_health, 0)
        
        # Create health progression data (simulated timeline)
        health_progression = {
            "labels": ["Previous", "Current", "Target"],
            "scores": [
                max(0, current_health_score - 10),  # Previous
                current_health_score,                # Current
                min(100, current_health_score + 15)  # Target
            ],
            "health_status": overall_health
        }
        
        # Extract lab values for comparison chart
        # Normalize values for better visualization
        lab_comparison = []
        
        for test in lab_results[:6]:  # Limit to 6 tests for readability
            test_name = test.get("test_name", "Unknown")
            value_str = test.get("value", "0")
            unit = test.get("unit", "")
            
            # Try to parse numeric value
            try:
                value = float(value_str)
            except (ValueError, TypeError):
                value = 0
            
            lab_comparison.append({
                "test_name": test_name,
                "value": value,
                "unit": unit,
                "display_value": f"{value_str} {unit}".strip()
            })
        
        return {
            "health_progression": health_progression,
            "lab_comparison": lab_comparison,
            "overall_health": overall_health,
            "health_score": current_health_score
        }
    
    def structure_clinic_chart_data(self, structured_data: dict, 
                                   analysis_result: dict) -> dict:
        """
        Structure data for clinic-facing visualizations with more detail.
        
        Args:
            structured_data: Raw lab values from Extractor
            analysis_result: Medical analysis results
            
        Returns:
            Dictionary with structured chart data for clinic view
        """
        print("   Structuring Clinic Chart Data (Visualization Agent)...")
        
        lab_results = structured_data.get("lab_results", [])
        
        # Chart 1: Lab values overview (up to 8 tests)
        lab_overview = []
        for test in lab_results[:8]:
            test_name = test.get("test_name", "Unknown")
            value_str = test.get("value", "0")
            unit = test.get("unit", "")
            
            try:
                value = float(value_str)
            except (ValueError, TypeError):
                value = 0
            
            lab_overview.append({
                "test_name": test_name,
                "value": value,
                "unit": unit,
                "display_value": f"{value_str} {unit}".strip()
            })
        
        # Chart 2: Values vs Reference Ranges
        reference_comparison = []
        
        for test in lab_results[:6]:  # Limit to 6 for readability
            test_name = test.get("test_name", "Unknown")
            value_str = test.get("value", "0")
            unit = test.get("unit", "")
            ref_range = test.get("reference_range") or test.get("ref_range", "")
            
            try:
                value = float(value_str)
            except (ValueError, TypeError):
                value = 0
            
            # Parse reference range if available
            ref_min, ref_max = self._parse_reference_range(ref_range, value)
            
            reference_comparison.append({
                "test_name": test_name,
                "value": value,
                "unit": unit,
                "display_value": f"{value_str} {unit}".strip(),
                "reference_range": ref_range,
                "ref_min": ref_min,
                "ref_max": ref_max,
                "status": self._get_status(value, ref_min, ref_max)
            })
        
        return {
            "lab_overview": lab_overview,
            "reference_comparison": reference_comparison
        }
    
    def _parse_reference_range(self, ref_range: str, current_value: float) -> tuple:
        """
        Parse reference range string to extract min and max values.
        
        Args:
            ref_range: Reference range string (e.g., "13.5-17.5 g/dL")
            current_value: Current test value for fallback
            
        Returns:
            Tuple of (min, max)
        """
        if not ref_range:
            # If no reference range, create a reasonable range around current value
            return (current_value * 0.8, current_value * 1.2)
        
        try:
            # Try to extract numbers from reference range
            import re
            numbers = re.findall(r'[\d.]+', ref_range)
            
            if len(numbers) >= 2:
                return (float(numbers[0]), float(numbers[1]))
            elif len(numbers) == 1:
                # Only one number found, use it as median
                median = float(numbers[0])
                return (median * 0.9, median * 1.1)
            else:
                # No numbers found
                return (current_value * 0.8, current_value * 1.2)
        except:
            return (current_value * 0.8, current_value * 1.2)
    
    def _get_status(self, value: float, ref_min: float, ref_max: float) -> str:
        """
        Determine if value is within, above, or below reference range.
        
        Args:
            value: Test value
            ref_min: Reference range minimum
            ref_max: Reference range maximum
            
        Returns:
            Status string: "normal", "high", or "low"
        """
        if value < ref_min:
            return "low"
        elif value > ref_max:
            return "high"
        else:
            return "normal"


if __name__ == "__main__":
    # Test the Visualization Agent
    agent = VisualizationAgent()
    
    test_structured_data = {
        "lab_results": [
            {"test_name": "Hemoglobin", "value": "13.5", "unit": "g/dL", "reference_range": "13.5-17.5 g/dL"},
            {"test_name": "WBC", "value": "7.2", "unit": "×10³/μL", "reference_range": "4.5-11.0 ×10³/μL"},
            {"test_name": "RBC", "value": "4.8", "unit": "×10⁶/μL", "reference_range": "4.5-5.5 ×10⁶/μL"},
            {"test_name": "Platelets", "value": "250", "unit": "×10³/μL", "reference_range": "150-400 ×10³/μL"},
            {"test_name": "Hematocrit", "value": "42", "unit": "%", "reference_range": "40-52%"},
            {"test_name": "MCV", "value": "88", "unit": "fL", "reference_range": "80-100 fL"}
        ]
    }
    
    test_analysis = {
        "health_summary": {
            "overall_health_reading": "Good"
        },
        "detailed_analysis": {
            "abnormalities": []
        }
    }
    
    print("\n" + "="*80)
    print("PATIENT CHART DATA")
    print("="*80)
    patient_data = agent.structure_patient_chart_data(test_structured_data, test_analysis)
    print(json.dumps(patient_data, indent=2))
    
    print("\n" + "="*80)
    print("CLINIC CHART DATA")
    print("="*80)
    clinic_data = agent.structure_clinic_chart_data(test_structured_data, test_analysis)
    print(json.dumps(clinic_data, indent=2))
