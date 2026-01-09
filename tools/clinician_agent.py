import os
import json
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()


class ClinicianSummaryAgent:
    """
    Agent responsible for generating concise, professional clinical summaries
    with highlighted abnormal values, reference ranges, and evidence-based context.
    """
    
    def __init__(self):
        # Use dedicated clinician API key, fallback to analysis key for backward compatibility
        groq_api_key = os.getenv("GROQ_CLINICIAN_API_KEY") or os.getenv("GROQ_ANALYSIS_API_KEY")
        if not groq_api_key:
            raise ValueError("GROQ_CLINICIAN_API_KEY or GROQ_ANALYSIS_API_KEY is required for Clinician Agent")
        
        self.client = OpenAI(
            api_key=groq_api_key,
            base_url="https://api.groq.com/openai/v1"
        )
        self.model = "llama-3.3-70b-versatile"
    
    def generate_clinician_summary(self, structured_data: dict, analysis_result: dict,
                                   research_findings: dict) -> dict:
        """
        Generate professional clinical summary for healthcare providers.
        
        Args:
            structured_data: Raw lab values from Extractor
            analysis_result: Medical analysis from Analyser
            research_findings: Research evidence from Research Agent
        
        Returns:
            Dictionary with clinical summary in professional format
        """
        print("   Generating Clinical Summary (Clinician Agent)...")
        
        # Extract key information
        abnormalities = analysis_result.get("detailed_analysis", {}).get("abnormalities", [])
        overall_health = analysis_result.get("health_summary", {}).get("overall_health_reading", "Unknown")
        
        # Build context from research findings
        clinician_context = research_findings.get("clinician_summary", "")
        evidence_sources = research_findings.get("evidence_sources", [])
        
        system_prompt = """You are a Clinical Decision Support AI generating concise summaries for physicians.

Your responsibilities:
1. Create BULLET-POINT summaries (no paragraphs or storytelling)
2. Highlight CRITICAL and ABNORMAL values with clear indicators (↑ ↓)
3. Display values WITH units and reference ranges
4. Provide clinical significance backed by evidence
5. Cite sources (PubMed IDs, MedlinePlus URLs)
6. Suggest follow-up actions based on clinical guidelines
7. Use professional medical terminology

DO NOT:
- Simplify or "dumb down" medical terms
- Write in narrative/story format
- Omit units or reference ranges
- Make definitive diagnoses

Return ONLY valid JSON in this exact format:
{
    "critical_findings": [
        {
            "test": "Test Name",
            "value": "X.X",
            "unit": "unit",
            "reference_range": "min - max unit",
            "status": "↑ High / ↓ Low / ‼️ Critical",
            "clinical_significance": "Brief clinical interpretation",
            "evidence": "Source citation (PMID, URL)"
        }
    ],
    "normal_findings": ["Test 1 (value unit)", "Test 2 (value unit)"],
    "clinical_context": "One-line pattern summary (e.g., 'Pattern consistent with mild normocytic anemia')",
    "recommendations": ["Action 1", "Action 2"],
    "differential_considerations": ["Condition 1", "Condition 2"]
}"""

        user_prompt = f"""Lab Report Data:
{json.dumps(structured_data, indent=2)}

Medical Analysis:
Overall Health Status: {overall_health}
Abnormalities Detected: {len(abnormalities)}

Detailed Abnormalities:
{json.dumps(abnormalities, indent=2)}

Research Evidence:
{clinician_context}

Evidence Sources:
{json.dumps(evidence_sources, indent=2)}

Task: Create a professional clinical summary with marked abnormal values and evidence-based recommendations."""

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                response_format={"type": "json_object"},
                temperature=0.2  # Lower for clinical precision
            )
            
            clinician_summary = json.loads(response.choices[0].message.content)
            
            # Add metadata
            clinician_summary["agent"] = "ClinicianSummaryAgent"
            clinician_summary["overall_health_status"] = overall_health
            clinician_summary["evidence_sources"] = evidence_sources
            
            print("   Clinical Summary Generated Successfully")
            return clinician_summary
            
        except Exception as e:
            print(f"   Error generating clinician summary: {e}")
            return {
                "error": str(e),
                "critical_findings": [],
                "clinical_context": "Error generating summary",
                "recommendations": ["Manual review required"],
                "agent": "ClinicianSummaryAgent"
            }


if __name__ == "__main__":
    # Test the Clinician Agent
    agent = ClinicianSummaryAgent()
    
    test_structured_data = {
        "Hemoglobin (Hb)": {"value": "12.5", "unit": "g/dL", "ref_range": "13.0 - 17.0"},
        "Packed Cell Volume (PCV)": {"value": "57.5", "unit": "%", "ref_range": "40 - 50"},
        "Neutrophils": {"value": "60", "unit": "%", "ref_range": "50 - 62"},
        "Platelet Count": {"value": "150000", "unit": "cumm", "ref_range": "150000 - 410000"}
    }
    
    test_analysis = {
        "health_summary": {
            "overall_health_reading": "Moderate",
            "summary_text": "Some abnormalities requiring attention",
            "key_findings": ["Low Hemoglobin", "High PCV"]
        },
        "detailed_analysis": {
            "abnormalities": [
                {
                    "test": "Hemoglobin (Hb)",
                    "status": "Low",
                    "implication": "May indicate anemia or iron deficiency",
                    "value": "12.5",
                    "unit": "g/dL"
                },
                {
                    "test": "Packed Cell Volume (PCV)",
                    "status": "High",
                    "implication": "May indicate dehydration or polycythemia",
                    "value": "57.5",
                    "unit": "%"
                }
            ],
            "lifestyle_recommendations": ["Hydration assessment", "Iron studies"]
        }
    }
    
    test_research = {
        "clinician_summary": "Anemia workup indicated. Consider iron studies and reticulocyte count.",
        "evidence_sources": [
            "https://pubmed.ncbi.nlm.nih.gov/12345678/",
            "https://medlineplus.gov/anemia.html"
        ]
    }
    
    result = agent.generate_clinician_summary(test_structured_data, test_analysis, test_research)
    print("\n" + "="*80)
    print("CLINICIAN AGENT OUTPUT")
    print("="*80)
    print(json.dumps(result, indent=2))
