import os
import re
import json
from pathlib import Path
from datetime import datetime
from tkinter import Tk, filedialog

from dotenv import load_dotenv
from pymongo import MongoClient
from bson import ObjectId

from openai import OpenAI

from tools.main_research_agent import ResearchOrchestrator

import pytesseract
from PIL import Image
from PyPDF2 import PdfReader

load_dotenv()


class MongoDBHandler:
    def __init__(self, connection_string, database_name="health_reports"):
        try:
            import certifi
            self.client = MongoClient(
                connection_string,
                tlsCAFile=certifi.where(),
                serverSelectionTimeoutMS=10000
            )
            self.db = self.client[database_name]
            self.reports_collection = self.db["lab_reports"]
            self.reports_collection.create_index([("user_id", 1), ("processed_timestamp", -1)])
            print("Connected to MongoDB successfully")
        except Exception as e:
            raise Exception(f"Failed to connect to MongoDB: {str(e)}")

    def store_lab_report(self, user_id, processed_data, file_name=None):
        try:
            ts = datetime.utcnow()

            report_document = {
                "user_id": user_id,
                "report_id": str(ObjectId()),
                "file_name": file_name,
                "processed_timestamp": ts,
                "structured_data": processed_data.get("structured_data", {}),
                "health_summary": processed_data.get("health_summary", {}),
                "detailed_analysis": processed_data.get("detailed_analysis", {}),
                "research_findings": processed_data.get("research_findings", {}),
                "overall_health_reading": processed_data.get("health_summary", {}).get("overall_health_reading",
                                                                                       "Unknown")
            }
            self.reports_collection.insert_one(report_document)
            print(f"Lab report stored successfully (ID: {report_document['report_id']})")
            return report_document['report_id']
        except Exception as e:
            raise Exception(f"Error storing lab report: {str(e)}")

    def close_connection(self):
        self.client.close()
        print("MongoDB connection closed")



class LabReportProcessor:
    def __init__(self):
        groq_extraction_key = os.getenv("GROQ_EXTRACTION_API_KEY")
        if not groq_extraction_key:
            raise ValueError("CRITICAL: GROQ_EXTRACTION_API_KEY is missing from .env file!")

        print(f"   [Debug] Groq Extraction Key loaded: {groq_extraction_key[:8]}...")

        self.groq_extraction_client = OpenAI(
            api_key=groq_extraction_key,
            base_url="https://api.groq.com/openai/v1"
        )
        self.groq_extraction_model = "llama-3.3-70b-versatile"

        groq_analysis_key = os.getenv("GROQ_ANALYSIS_API_KEY")
        if not groq_analysis_key:
            raise ValueError("CRITICAL: GROQ_ANALYSIS_API_KEY is missing from .env file!")

        print(f"   [Debug] Groq Analysis Key loaded: {groq_analysis_key[:8]}...")

        self.groq_analysis_client = OpenAI(
            api_key=groq_analysis_key,
            base_url="https://api.groq.com/openai/v1"
        )
        self.groq_analysis_model = "llama-3.3-70b-versatile"

    def extract_text_from_pdf(self, pdf_path):
        text = ""
        try:
            with open(pdf_path, 'rb') as file:
                pdf_reader = PdfReader(file)
                for page in pdf_reader.pages:
                    text += page.extract_text() or ""
            return self.clean_text(text)
        except Exception as e:
            print(f"Error reading PDF: {e}")
            return ""

    def extract_text_from_image(self, image_path):
        try:
            image = Image.open(image_path)
            text = pytesseract.image_to_string(image)
            return self.clean_text(text)
        except Exception as e:
            print(f"Error reading Image: {e}")
            return ""

    def clean_text(self, text):
        text = re.sub(r'\\s+', ' ', text)
        return text.strip()

    def read_report(self, file_path):
        ext = Path(file_path).suffix.lower()
        if ext == '.pdf':
            return self.extract_text_from_pdf(file_path)
        elif ext in ['.jpg', '.jpeg', '.png', '.bmp']:
            return self.extract_text_from_image(file_path)
        else:
            raise ValueError(f"Unsupported file type: {ext}")

    def extract_structured_data_groq(self, raw_text):
        print("   Sending to Groq Agent 1 for JSON extraction...")

        system_prompt = """You are a specialized Data Extraction Agent. Extract lab report values into precise JSON. Do not explain. Return JSON only. Format per test: {"test_name": "...", "value": "...", "unit": "...", "ref_range": "..."}"""

        try:
            response = self.groq_extraction_client.chat.completions.create(
                model=self.groq_extraction_model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"Extract this report:\\n{raw_text}"}
                ],
                response_format={"type": "json_object"},
                temperature=0.1
            )

            json_text = response.choices[0].message.content
            return json.loads(json_text)
        except Exception as e:
            print(f"Groq Extraction Error: {e}")
            raise e

    def research_findings(self, structured_data, analysis_result):
        print("   Sending to Research Agent 3 for Evidence Gathering...")

        try:
            research_input = {
                "patient_demographics": structured_data.get("patient_demographics", {
                    "name": "Patient",
                    "age": "Unknown",
                    "sex": "Unknown"
                }),
                "lab_results": []
            }

            abnormalities = analysis_result.get("detailed_analysis", {}).get("abnormalities", [])

            for abnormality in abnormalities:
                lab_entry = {
                    "test": abnormality.get("test", "Unknown Test"),
                    "value": abnormality.get("value", "N/A"),
                    "unit": abnormality.get("unit", ""),
                    "flag": abnormality.get("status", "Abnormal")
                }
                research_input["lab_results"].append(lab_entry)

            if not research_input["lab_results"]:
                print("   [Skipped] No abnormalities to research")
                return {
                    "patient_explainer": "No significant abnormalities requiring research.",
                    "clinician_summary": "All values within normal ranges.",
                    "evidence_sources": []
                }

            orchestrator = ResearchOrchestrator()
            research_report = orchestrator.analyze_and_research(research_input)

            print("Research Evidence Gathered (Research Agent 3)")

            return {
                "full_report": research_report,
                "patient_explainer": self._extract_section(research_report, "PATIENT EXPLAINER"),
                "clinician_summary": self._extract_section(research_report, "CLINICIAN SUMMARY"),
                "evidence_sources": self._extract_citations(research_report)
            }

        except Exception as e:
            print(f"Research Agent Error: {e}")
            return {
                "error": str(e),
                "patient_explainer": "Research temporarily unavailable.",
                "clinician_summary": "Unable to fetch clinical evidence.",
                "evidence_sources": []
            }

    def _extract_section(self, markdown_text, section_name):
        try:
            lines = markdown_text.split('\\n')
            section_lines = []
            in_section = False

            for line in lines:
                if section_name.upper() in line.upper():
                    in_section = True
                    continue
                elif in_section and line.strip().startswith('#'):
                    break
                elif in_section:
                    section_lines.append(line)

            return '\\n'.join(section_lines).strip()
        except:
            return markdown_text

    def _extract_citations(self, markdown_text):
        import re
        urls = re.findall(r'https?://[^\\s)]+', markdown_text)
        return urls

    def analyze_with_groq(self, structured_data):
        print("   Sending to Groq Agent 2 for Medical Analysis...")

        system_prompt = """You are a Medical Analysis AI specialized in interpreting lab reports. Your task: 1. Analyze the provided lab data thoroughly 2. Categorize overall health status as exactly one of: Danger, Moderate, Good, Excellent 3. Provide a comprehensive summary and detailed breakdown 4. Return ONLY valid JSON, no markdown or explanations. Output format: {"health_summary": {"overall_health_reading": "Danger/Moderate/Good/Excellent", "summary_text": "Patient-friendly summary...", "key_findings": ["Finding 1", "Finding 2"]}, "detailed_analysis": {"abnormalities": [{"test": "name", "status": "High/Low/Critical", "implication": "..."}], "lifestyle_recommendations": ["rec 1", "rec 2"]}}"""

        user_prompt = f"""Analyze the following lab data and provide a comprehensive medical analysis: {json.dumps(structured_data, indent=2)}. Provide your analysis in the JSON format specified."""


        try:
            response = self.groq_analysis_client.chat.completions.create(
                model=self.groq_analysis_model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                response_format={"type": "json_object"},
                temperature=0.3
            )

            json_text = response.choices[0].message.content
            return json.loads(json_text)
        except Exception as e:
            print(f"Groq Analysis Error: {e}")
            return {
                "health_summary": {
                    "overall_health_reading": "Error",
                    "summary_text": f"Analysis failed: {str(e)}",
                    "key_findings": []
                },
                "detailed_analysis": {
                    "abnormalities": [],
                    "lifestyle_recommendations": []
                }
            }

    def process_lab_report(self, file_path):
        print(f"\\nProcessing: {os.path.basename(file_path)}")

        raw_text = self.read_report(file_path)
        if not raw_text:
            raise Exception("No text extracted from file.")
        print(f"Extracted {len(raw_text)} chars")

        structured_data = self.extract_structured_data_groq(raw_text)
        print("Data Structured (Groq Agent 1)")

        analysis_result = self.analyze_with_groq(structured_data)
        print("Analysis Complete (Groq Agent 2)")

        research_result = self.research_findings(structured_data, analysis_result)
        print("Research Complete (Research Agent 3)")

        return {
            "raw_text": raw_text,
            "structured_data": structured_data,
            "health_summary": analysis_result.get("health_summary", {}),
            "detailed_analysis": analysis_result.get("detailed_analysis", {}),
            "research_findings": research_result
        }



if __name__ == "__main__":
    MONGODB_URI = os.getenv("MONGODB_URI")

    processor = LabReportProcessor()
    db_handler = None

    try:
        root = Tk()
        root.withdraw()
        root.attributes('-topmost', True)

        file_path = filedialog.askopenfilename(
            title="Select Lab Report",
            filetypes=[("PDF/Images", "*.pdf *.png *.jpg *.jpeg")]
        )

        if file_path:
            result = processor.process_lab_report(file_path)

            if MONGODB_URI:
                db_handler = MongoDBHandler(MONGODB_URI)
                report_id = db_handler.store_lab_report(
                    user_id="user_12345",
                    processed_data=result,
                    file_name=os.path.basename(file_path)
                )
            else:
                print("\\n[DB Skipped] MongoDB URI not set.")
                print(json.dumps(result['health_summary'], indent=2))

    except Exception as e:
        print(f"\\nCRITICAL ERROR: {e}")
    finally:
        if db_handler:
            db_handler.close_connection()