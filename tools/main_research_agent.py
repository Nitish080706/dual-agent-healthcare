from openai import OpenAI
import os
import json
from .researcher import MedicalResearcher
from dotenv import load_dotenv

load_dotenv()

class ResearchOrchestrator:
    def __init__(self):
        api_key = os.getenv("GROQ_RESEARCH_API_KEY") or os.getenv("GROQ_ANALYSIS_API_KEY")
        if not api_key:
            raise ValueError("GROQ_RESEARCH_API_KEY or GROQ_ANALYSIS_API_KEY required")
        
        self.client = OpenAI(
            base_url="https://api.groq.com/openai/v1",
            api_key=api_key
        )
        self.researcher = MedicalResearcher()
        self.model = "llama-3.3-70b-versatile"

    def analyze_and_research(self, extracted_data: dict, rag_context: list = None):
        print(f"--- 1. ANALYZING REPORT FOR: {extracted_data.get('patient_demographics', {}).get('name', 'Patient')} ---")

        plan_prompt = f"""
        You are a Clinical Research Assistant. 
        Here is the patient's lab extracted data:
        {json.dumps(extracted_data, indent=2)}

        Identify the Top 1 or 2 most critical/abnormal findings.
        For each finding, generate:
        1. A 'medline_term' (Simple noun) to define it for the patient (e.g., "HbA1c").
        2. A 'pubmed_query' (Complex string) to find the most relevant clinical evidence.
           - If it is a common disease (Diabetes, Lipids), search for "Management Guidelines 2024".
           - If it is a detailed pattern (Low MCV + Normal Iron), search for "Differential Diagnosis".
           - If it is a drug/toxicity, search for "Adverse Effects" or "Interaction".
        
        Return ONLY valid JSON like this:
        {{
            "critical_items": [
                {{
                    "finding_name": "HbA1c",
                    "value": "6.5%",
                    "medline_term": "HbA1c test",
                    "pubmed_query": "HbA1c 6.5 diabetes diagnosis standards of care 2024"
                }}
            ]
        }}
        """
        
        completion = self.client.chat.completions.create(
            messages=[{"role": "system", "content": "You are a JSON-only response bot."},
                      {"role": "user", "content": plan_prompt}],
            model=self.model,
            temperature=0,
            response_format={"type": "json_object"}
        )
        
        research_plan = json.loads(completion.choices[0].message.content)
        print(f"\n[Plan] Research Needed For: {[item['finding_name'] for item in research_plan.get('critical_items', [])]}")

        final_evidence = []
        
        for item in research_plan.get("critical_items", []):
            print(f"\n--- RESEARCHING: {item['finding_name']} ---")
            
            medline_res = self.researcher.search_medline_definition(item['medline_term'])
            pubmed_res = self.researcher.search_pubmed_evidence(item['pubmed_query'])
            
            evidence_packet = {
                "finding": item['finding_name'],
                "value": item['value'],
                "patient_definition": medline_res,
                "clinical_guidelines": pubmed_res[0] if pubmed_res else None 
            }
            final_evidence.append(evidence_packet)

        return self._generate_final_report(extracted_data, final_evidence, rag_context)

    def _generate_final_report(self, extracted_data, evidence, rag_context=None):
        synthesis_prompt = f"""
        You are a Medical AI Assistant. Write a comprehensive report by combining authoritative medical reference data (RAG) and current clinical evidence (Internet).
        
        PATIENT DATA: {json.dumps(extracted_data)}
        
        VERIFIED INTERNET RESEARCH EVIDENCE:
        {json.dumps(evidence, indent=2)}
        
        MEDICAL REFERENCE DATA (RAG):
        {json.dumps(rag_context, indent=2) if rag_context else "No reference data available."}
        
        TASK:
        Write a report with the following two sections. Merge the RAG knowledge (definitions, standard ranges) with the Internet evidence (recent guidelines, citations).
        
        1. PATIENT EXPLAINER
        - Simple language.
        - Use the 'patient_definition' text exactly as provided.
        - Include the MedlinePlus URL.
        
        2. CLINICIAN SUMMARY
        - Professional tone.
        - Cite the 'clinical_guidelines' (Title + URL).
        - Suggest management based on that evidence.
        """
        
        completion = self.client.chat.completions.create(
            messages=[{"role": "user", "content": synthesis_prompt}],
            model=self.model,
            temperature=0.2
        )
        
        return completion.choices[0].message.content

if __name__ == "__main__":
    real_sterling_data = {
        "patient_demographics": {"name": "Mr. Hardik Sompura", "age": "41", "sex": "Male"},
        "lab_results": [
            {"test": "Glycated Haemoglobin (HbA1c)", "value": "8.2", "unit": "%", "flag": "High"},
            {"test": "Mean Blood Glucose", "value": "190", "unit": "mg/dL", "flag": "High"}
        ]
    }
    
    agent = ResearchOrchestrator()
    final_report = agent.analyze_and_research(real_sterling_data)
    
    print("\n\n" + "="*40)
    print("FINAL AGENT OUTPUT (From Research Loop)")
    print("="*40)
    print(final_report)
