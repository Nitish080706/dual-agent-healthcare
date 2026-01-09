import os
import json
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()


class PatientExplainerAgent:
    """
    Agent responsible for translating medical lab report findings into 
    patient-friendly language with clear disclaimers and actionable questions.
    """
    
    def __init__(self):
        # Use dedicated patient API key, fallback to analysis key for backward compatibility
        groq_api_key = os.getenv("GROQ_PATIENT_API_KEY") or os.getenv("GROQ_ANALYSIS_API_KEY")
        if not groq_api_key:
            raise ValueError("GROQ_PATIENT_API_KEY or GROQ_ANALYSIS_API_KEY is required for Patient Agent")
        
        self.client = OpenAI(
            api_key=groq_api_key,
            base_url="https://api.groq.com/openai/v1"
        )
        self.model = "llama-3.3-70b-versatile"
    
    def generate_patient_summary(self, structured_data: dict, analysis_result: dict, 
                                 research_findings: dict) -> dict:
        """
        Generate patient-friendly explanation of lab results.
        
        Args:
            structured_data: Raw lab values from Extractor
            analysis_result: Medical analysis from Analyser
            research_findings: Research evidence from Research Agent
        
        Returns:
            Dictionary with patient-friendly summary
        """
        print("   Generating Patient-Friendly Summary (Patient Agent)...")
        
        # Extract key information
        abnormalities = analysis_result.get("detailed_analysis", {}).get("abnormalities", [])
        overall_health = analysis_result.get("health_summary", {}).get("overall_health_reading", "Unknown")
        
        # Build context from research findings
        patient_explainer_context = research_findings.get("patient_explainer", "")
        evidence_sources = research_findings.get("evidence_sources", [])
        
        system_prompt = """You are a compassionate health communicator translating medical lab results for patients.

Your responsibilities:
1. Use SIMPLE, NON-MEDICAL language (avoid jargon like "erythrocytes", use "red blood cells")
2. Explain what each test measures in everyday terms
3. Clearly state what is normal vs. what needs attention
4. Provide actionable "Questions to ask your doctor"
5. Always include a clear disclaimer that this is NOT a diagnosis
6. Be reassuring but honest about findings
7. Focus on what the patient can understand and act on

DO NOT:
- Use complex medical terminology without explanation
- Provide specific treatment recommendations
- Make diagnoses
- Cause unnecessary alarm

Return ONLY valid JSON in this exact format:
{
    "plain_language_summary": "A 2-3 sentence overview in simple terms",
    "what_is_normal": ["Test Name 1", "Test Name 2"],
    "needs_attention": [
        {
            "test": "Test Name",
            "patient_explanation": "What this test measures in simple terms",
            "your_result": "Your value (unit)",
            "what_it_means": "Simple explanation of what this result suggests",
            "next_steps": "What you should do next"
        }
    ],
    "questions_for_doctor": ["Question 1?", "Question 2?"],
    "disclaimer": "Standard medical disclaimer"
}"""

        user_prompt = f"""Patient's Lab Results:
{json.dumps(structured_data, indent=2)}

Medical Analysis:
Overall Health: {overall_health}
Abnormalities Found: {len(abnormalities)}

Detailed Abnormalities:
{json.dumps(abnormalities, indent=2)}

Medical Research Context:
{patient_explainer_context}

Evidence Sources:
{json.dumps(evidence_sources, indent=2)}

Task: Create a patient-friendly summary that helps them understand their results without medical training."""

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                response_format={"type": "json_object"},
                temperature=0.4  # Slightly higher for natural language
            )
            
            patient_summary = json.loads(response.choices[0].message.content)
            
            # Add metadata
            patient_summary["agent"] = "PatientExplainerAgent"
            patient_summary["overall_health_status"] = overall_health
            
            print("   Patient Summary Generated Successfully")
            return patient_summary
            
        except Exception as e:
            print(f"   Error generating patient summary: {e}")
            return {
                "error": str(e),
                "plain_language_summary": "We encountered an error creating your personalized summary.",
                "disclaimer": "This information is not a substitute for professional medical advice. Please consult your healthcare provider.",
                "agent": "PatientExplainerAgent"
            }


if __name__ == "__main__":
    # Test the Patient Agent
    agent = PatientExplainerAgent()
    
    test_structured_data = {
        "Hemoglobin (Hb)": {"value": "12.5", "unit": "g/dL", "ref_range": "13.0 - 17.0"},
        "Packed Cell Volume (PCV)": {"value": "57.5", "unit": "%", "ref_range": "40 - 50"},
        "Neutrophils": {"value": "60", "unit": "%", "ref_range": "50 - 62"}
    }
    
    test_analysis = {
        "health_summary": {
            "overall_health_reading": "Moderate",
            "summary_text": "Some abnormalities detected",
            "key_findings": ["Low Hemoglobin", "High PCV"]
        },
        "detailed_analysis": {
            "abnormalities": [
                {
                    "test": "Hemoglobin (Hb)",
                    "status": "Low",
                    "implication": "May indicate anemia or iron deficiency"
                },
                {
                    "test": "Packed Cell Volume (PCV)",
                    "status": "High",
                    "implication": "May indicate dehydration or polycythemia"
                }
            ]
        }
    }
    
    test_research = {
        "patient_explainer": "Hemoglobin is a protein in red blood cells that carries oxygen. Low levels may cause fatigue.",
        "evidence_sources": ["https://medlineplus.gov/hemoglobin"]
    }
    
    result = agent.generate_patient_summary(test_structured_data, test_analysis, test_research)
    print("\n" + "="*80)
    print("PATIENT AGENT OUTPUT")
    print("="*80)
    print(json.dumps(result, indent=2))
