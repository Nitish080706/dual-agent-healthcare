import requests
import xml.etree.ElementTree as ET
import time
import json
from typing import List, Dict, Optional

class MedicalResearcher:

    def __init__(self, email="ai_agent@example.com"):
        self.email = email 
        self.medline_base = "https://wsearch.nlm.nih.gov/ws/query"
        self.pubmed_base = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"

    def search_medline_definition(self, term: str) -> Dict[str, str]:
        try:
            params = {
                "db": "healthTopics",
                "term": term,
                "retmax": 1,
                "rettype": "brief"
            }
            response = requests.get(self.medline_base, params=params)
            response.raise_for_status()

            root = ET.fromstring(response.content)
            
            doc = root.find(".//document")
            if doc is None:
                return {"title": term, "definition": "No official definition found.", "url": ""}

            title = doc.find(".//content[@name='title']").text
            snippet = doc.find(".//content[@name='snippet']").text
            url = doc.get('url')

            clean_snippet = snippet.replace('<span class="qt0">', '').replace('</span>', '').replace('<span class="qt1">', '')

            return {
                "source": "MedlinePlus (National Library of Medicine)",
                "title": title,
                "definition": clean_snippet,
                "url": url
            }
        except Exception as e:
            print(f"Medline Error: {e}")
            return {"error": str(e)}

    def search_pubmed_evidence(self, query: str) -> List[Dict]:
        try:
            search_params = {
                "db": "pubmed",
                "term": query,
                "retmax": 3,
                "retmode": "json",
                "email": self.email,
                "sort": "relevance"
            }
            search_resp = requests.get(f"{self.pubmed_base}/esearch.fcgi", params=search_params)
            search_data = search_resp.json()
            
            id_list = search_data.get("esearchresult", {}).get("idlist", [])
            if not id_list:
                return []

            ids_str = ",".join(id_list)
            fetch_params = {
                "db": "pubmed",
                "id": ids_str,
                "retmode": "xml",
                "email": self.email
            }
            fetch_resp = requests.get(f"{self.pubmed_base}/efetch.fcgi", params=fetch_params)
            
            root = ET.fromstring(fetch_resp.content)
            articles = []
            
            for article in root.findall(".//PubmedArticle"):
                title = article.find(".//ArticleTitle").text
                
                abstract_node = article.find(".//Abstract")
                abstract_text = ""
                if abstract_node is not None:
                    texts = [elem.text for elem in abstract_node.findall("AbstractText") if elem.text]
                    abstract_text = " ".join(texts)
                
                pmid = article.find(".//PMID").text
                link = f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/"

                articles.append({
                    "source": "PubMed",
                    "title": title,
                    "summary": abstract_text[:500] + "...",
                    "url": link
                })
                
            return articles

        except Exception as e:
            print(f"PubMed Error: {e}")
            return []

if __name__ == "__main__":
    tool = MedicalResearcher()
    
    print("--- PATIENT SEARCH: High Cholesterol ---")
    print(json.dumps(tool.search_medline_definition("High Cholesterol"), indent=2))
    
    print("\n--- CLINICIAN SEARCH: Statin Guidelines ---")
    print(json.dumps(tool.search_pubmed_evidence("Statin therapy guidelines 2024"), indent=2))
