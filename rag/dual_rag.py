import os
import pickle
from typing import List, Dict
import numpy as np
from rank_bm25 import BM25Okapi
import chromadb
from chromadb.config import Settings
from chromadb.utils import embedding_functions
from groq import Groq
from pathlib import Path
from dotenv import load_dotenv
load_dotenv()
import pdfplumber


class MedicalRAGSystem:
    def __init__(self, groq_api_key: str, persist_dir: str = "./rag_storage"):
        """Initialize the RAG system with Groq API and ChromaDB"""
        self.groq_client = Groq(api_key=groq_api_key)
        self.persist_dir = Path(persist_dir)
        self.persist_dir.mkdir(exist_ok=True)
        
        # Initialize ChromaDB with persistence
        self.chroma_client = chromadb.PersistentClient(
            path=str(self.persist_dir / "chromadb")
        )
        
        # Use a truly offline custom embedding function (no model downloads)
        # This creates simple TF-IDF-like embeddings locally
        self.embedding_function = self._create_offline_embedding_function()
        
        # Create or get collection with local embedding function
        # If there's an embedding function conflict, delete and recreate the collection
        try:
            self.collection = self.chroma_client.get_or_create_collection(
                name="medical_reports",
                embedding_function=self.embedding_function,
                metadata={"hnsw:space": "cosine"}
            )
        except ValueError as e:
            if "embedding function conflict" in str(e).lower():
                print("Detected old embedding function. Recreating collection with offline embedding...")
                try:
                    self.chroma_client.delete_collection("medical_reports")
                except:
                    pass
                self.collection = self.chroma_client.get_or_create_collection(
                    name="medical_reports",
                    embedding_function=self.embedding_function,
                    metadata={"hnsw:space": "cosine"}
                )
            else:
                raise
        
        self.documents = []
        self.bm25 = None
        self.bm25_path = self.persist_dir / "bm25_index.pkl"
        self.docs_path = self.persist_dir / "documents.pkl"
        
        # Try to load existing data
        self.load_index()
    
    def _create_offline_embedding_function(self):
        """Create a simple offline embedding function that doesn't download models"""
        from chromadb.api.types import EmbeddingFunction
        
        class OfflineEmbeddingFunction(EmbeddingFunction):
            """Simple offline embedding using normalized word vectors"""
            
            def name(self) -> str:
                """Return the name of this embedding function"""
                return "offline_hash_embedding"
            
            def __call__(self, input: list[str]) -> list[list[float]]:
                """Generate simple embeddings from text without any model downloads"""
                embeddings = []
                
                for text in input:
                    # Create a simple bag-of-words style embedding
                    words = text.lower().split()
                    
                    # Use a fixed vocabulary size for consistent dimensionality
                    # Create a simple hash-based embedding (384 dimensions to match common models)
                    embedding = [0.0] * 384
                    
                    for word in words:
                        # Simple hash function to distribute words across dimensions
                        hash_val = hash(word) % 384
                        embedding[hash_val] += 1.0
                    
                    # Normalize the embedding
                    magnitude = sum(x**2 for x in embedding) ** 0.5
                    if magnitude > 0:
                        embedding = [x / magnitude for x in embedding]
                    
                    embeddings.append(embedding)
                
                return embeddings
        
        return OfflineEmbeddingFunction()
        

    def chunk_text(self, text: str, chunk_size: int = 1000, overlap: int = 200) -> List[str]:
        """Split text into overlapping chunks"""
        words = text.split()
        chunks = []
        
        for i in range(0, len(words), chunk_size - overlap):
            chunk = ' '.join(words[i:i + chunk_size])
            if chunk:
                chunks.append(chunk)
        
        return chunks
    
    def process_book(self, file_path: str, chunk_size: int = 1000, overlap: int = 200):
        """Process a large book and store it in chunks"""
        print(f"Processing book: {file_path}")
        
        # Detect file type
        content = ""
        if file_path.lower().endswith(".pdf"):
            try:
                import pdfplumber
                with pdfplumber.open(file_path) as pdf:
                    for page in pdf.pages:
                        text = page.extract_text()
                        if text:
                            content += text + "\n"
            except ImportError:
                print("pdfplumber not found, attempting PyPDF2...")
                from PyPDF2 import PdfReader
                reader = PdfReader(file_path)
                for page in reader.pages:
                    content += page.extract_text() + "\n"
        else:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
        
        if not content:
            print(f"Warning: No content extracted from {file_path}")
            return

        # Split into chunks
        chunks = self.chunk_text(content, chunk_size, overlap)
        print(f"Created {len(chunks)} chunks")
        
        # Create documents from chunks
        documents = []
        for i, chunk in enumerate(chunks):
            documents.append({
                'id': i + 1,
                'type': 'book_chunk',
                'title': f'Chunk {i+1}',
                'content': chunk,
                'source': os.path.basename(file_path)
            })
        
        # Add documents to the system
        self.add_documents(documents)
        print("Book processing complete!")

    def initialize_lab_reference_data(self, pdf_path: str = "rag/labreadingdata.pdf", retries: int = 2):
        """Initialize RAG with lab reading reference data if not already loaded"""
        stats = self.get_stats()
        if stats['total_documents'] > 0:
            print(f"RAG already contains {stats['total_documents']} documents. Skipping initialization.")
            return

        if os.path.exists(pdf_path):
            print(f"Initializing RAG with reference data from: {pdf_path}")
            for attempt in range(retries + 1):
                try:
                    self.process_book(pdf_path)
                    print("Successfully initialized RAG reference data.")
                    return
                except Exception as e:
                    if "timeout" in str(e).lower() and attempt < retries:
                        print(f"Network timeout during RAG initialization (Attempt {attempt + 1}/{retries + 1}). Retrying...")
                        continue
                    print(f"Error during RAG initialization: {str(e)}")
                    print("Medical RAG may have limited functionality (BM25 only if indexing failed).")
                    break
        else:
            print(f"Warning: Reference PDF not found at {pdf_path}")
        
    def add_documents(self, documents: List[Dict[str, str]]):
        """Add documents to both ChromaDB and BM25 index"""
        self.documents = documents
        
        print(f"Adding {len(documents)} documents to ChromaDB...")
        
        # Clear existing collection
        try:
            self.chroma_client.delete_collection("medical_reports")
        except:
            pass
        
        self.collection = self.chroma_client.get_or_create_collection(
            name="medical_reports",
            embedding_function=self.embedding_function,
            metadata={"hnsw:space": "cosine"}
        )
        
        # Add to ChromaDB in batches
        batch_size = 100
        for i in range(0, len(documents), batch_size):
            batch = documents[i:i+batch_size]
            ids = [str(doc['id']) for doc in batch]
            texts = [doc['content'] for doc in batch]
            metadatas = [
                {
                    'title': doc['title'],
                    'type': doc['type'],
                    'source': doc.get('source', 'unknown')
                } for doc in batch
            ]
            
            try:
                self.collection.add(
                    documents=texts,
                    metadatas=metadatas,
                    ids=ids
                )
            except Exception as e:
                print(f"Warning: Failed to add batch to ChromaDB: {str(e)}")
                if "timeout" in str(e).lower():
                    print("This is likely a network timeout while downloading the embedding model.")
                    print("Try running again with a stable internet connection.")
                # We continue so BM25 can still be built
            
            print(f"Added batch {i//batch_size + 1}/{(len(documents)-1)//batch_size + 1}")
        
        # Initialize BM25 - This part is local and shouldn't time out
        print("Building BM25 index...")
        tokenized_docs = [doc['content'].lower().split() for doc in documents]
        self.bm25 = BM25Okapi(tokenized_docs)
        
        # Save the index
        self.save_index()
        print(f"Successfully added and saved {len(documents)} documents (BM25 ready)")
    
    def save_index(self):
        """Save BM25 index and documents to disk"""
        print("Saving indexes...")
        
        # Save BM25 index
        with open(self.bm25_path, 'wb') as f:
            pickle.dump(self.bm25, f)
        
        # Save documents
        with open(self.docs_path, 'wb') as f:
            pickle.dump(self.documents, f)
        
        print("Indexes saved successfully!")
    
    def load_index(self):
        """Load BM25 index and documents from disk"""
        if self.bm25_path.exists() and self.docs_path.exists():
            print("Loading existing indexes...")
            
            with open(self.bm25_path, 'rb') as f:
                self.bm25 = pickle.load(f)
            
            with open(self.docs_path, 'rb') as f:
                self.documents = pickle.load(f)
            
            print(f"Loaded {len(self.documents)} documents from storage")
            return True
        return False
    
    def bm25_search(self, query: str, top_k: int = 5) -> List[Dict]:
        """Search using BM25 algorithm"""
        if not self.bm25:
            print("BM25 index not initialized!")
            return []
        
        tokenized_query = query.lower().split()
        scores = self.bm25.get_scores(tokenized_query)
        
        # Get top-k indices
        top_indices = np.argsort(scores)[-top_k:][::-1]
        
        results = []
        for idx in top_indices:
            if scores[idx] > 0:  # Only include relevant results
                results.append({
                    **self.documents[idx],
                    'score': scores[idx]
                })
        
        return results
    
    def vector_search(self, query: str, top_k: int = 5) -> List[Dict]:
        """Search using ChromaDB vector similarity"""
        try:
            results = self.collection.query(
                query_texts=[query],
                n_results=top_k
            )
            
            retrieved_docs = []
            for i, doc_id in enumerate(results['ids'][0]):
                doc = next((d for d in self.documents if str(d['id']) == doc_id), None)
                if doc:
                    retrieved_docs.append({
                        **doc,
                        'distance': results['distances'][0][i]
                    })
            
            return retrieved_docs
        except Exception as e:
            print(f"Vector search failed: {str(e)}")
            return []
    
    def hybrid_search(self, query: str, top_k: int = 5, 
                     bm25_weight: float = 0.6, 
                     vector_weight: float = 0.4) -> List[Dict]:
        """Combine BM25 and vector search results"""
        bm25_results = self.bm25_search(query, top_k=top_k*2)
        vector_results = self.vector_search(query, top_k=top_k*2)
        
        # Normalize scores
        bm25_scores = {doc['id']: doc['score'] for doc in bm25_results}
        max_bm25 = max(bm25_scores.values()) if bm25_scores else 1
        
        # For vector search, lower distance is better, so we invert it
        vector_scores = {doc['id']: 1 / (1 + doc['distance']) for doc in vector_results}
        max_vector = max(vector_scores.values()) if vector_scores else 1
        
        # Calculate hybrid scores
        hybrid_scores = {}
        all_doc_ids = set(bm25_scores.keys()) | set(vector_scores.keys())
        
        for doc_id in all_doc_ids:
            norm_bm25 = (bm25_scores.get(doc_id, 0) / max_bm25) if max_bm25 > 0 else 0
            norm_vector = (vector_scores.get(doc_id, 0) / max_vector) if max_vector > 0 else 0
            hybrid_scores[doc_id] = (bm25_weight * norm_bm25 + vector_weight * norm_vector)
        
        # Sort by hybrid score
        sorted_ids = sorted(hybrid_scores.items(), key=lambda x: x[1], reverse=True)[:top_k]
        
        results = []
        for doc_id, score in sorted_ids:
            doc = next((d for d in self.documents if d['id'] == doc_id), None)
            if doc:
                results.append({
                    **doc,
                    'hybrid_score': score
                })
        
        return results
    
    def generate_response(self, query: str, context_docs: List[Dict], research_findings: Dict = None) -> str:
        """Generate response using Groq LLM, optionally including research findings"""
        if not context_docs and not research_findings:
            return "No relevant information found to answer your question."
        
        # Build context from retrieved documents (RAG)
        rag_context = "\n\n".join([
            f"[Reference Section {i+1}]\n{doc['content']}"
            for i, doc in enumerate(context_docs)
        ])
        
        # Build context from internet research findings
        internet_context = ""
        if research_findings:
            internet_context = f"\n\n[Internet Research Findings]\n{json.dumps(research_findings, indent=2)}"

        # Create prompt
        system_content = (
            "You are a medical knowledge assistant. Combine the provided reference knowledge (RAG) "
            "with current internet research to provide a comprehensive answer. "
            "Structure your response with clear sections for both PATIENTS and CLINICIANS. "
            "Always cite whether information comes from the reference library or internet research."
        )
        
        user_content = (
            f"Question: {query}\n\n"
            f"REFERENCE KNOWLEDGE (RAG):\n{rag_context}\n\n"
            f"CURRENT INTERNET RESEARCH:\n{internet_context}\n\n"
            "Please provide a unified medical explanation."
        )

        messages = [
            {"role": "system", "content": system_content},
            {"role": "user", "content": user_content}
        ]
        
        # Call Groq API
        try:
            chat_completion = self.groq_client.chat.completions.create(
                messages=messages,
                model="mixtral-8x7b-32768",
                temperature=0.3,
                max_tokens=2048,
            )
            return chat_completion.choices[0].message.content
        except Exception as e:
            return f"Error generating response: {str(e)}"

    def get_reference_context(self, test_names: List[str], top_k: int = 3) -> List[Dict]:
        """Get RAG context for specific lab test names"""
        all_results = []
        for test in test_names:
            results = self.hybrid_search(test, top_k=top_k)
            all_results.extend(results)
        
        # Remove duplicates based on content
        unique_results = []
        seen_content = set()
        for res in all_results:
            if res['content'] not in seen_content:
                unique_results.append(res)
                seen_content.add(res['content'])
        
        return unique_results

    def query_with_research(self, abnormalities: List[Dict], research_findings: Dict = None) -> Dict:
        """Combine RAG medical knowledge with internet research for abnormalities"""
        test_names = [abn.get('test', '') for abn in abnormalities]
        relevant_docs = self.get_reference_context(test_names)
        
        query_str = f"Explain the significance of: {', '.join([f'{a['test']} ({a['value']})' for a in abnormalities])}"
        
        response = self.generate_response(query_str, relevant_docs, research_findings)
        
        return {
            'abnormalities': abnormalities,
            'rag_context': relevant_docs,
            'response': response
        }
    
    def query(self, question: str, search_type: str = "hybrid", top_k: int = 5) -> Dict:
        """Main query function"""
        print(f"\nQuery: {question}")
        print(f"Search Type: {search_type}\n")
        
        # Retrieve relevant documents
        if search_type == "bm25":
            relevant_docs = self.bm25_search(question, top_k=top_k)
        elif search_type == "vector":
            relevant_docs = self.vector_search(question, top_k=top_k)
        else:  # hybrid
            relevant_docs = self.hybrid_search(question, top_k=top_k)
        
        # Print retrieved documents
        print(f"Retrieved {len(relevant_docs)} relevant sections:")
        for i, doc in enumerate(relevant_docs, 1):
            score_key = 'hybrid_score' if 'hybrid_score' in doc else 'score' if 'score' in doc else 'distance'
            print(f"{i}. {doc['title']} (Score: {doc.get(score_key, 0):.4f})")
        
        # Generate response
        print("\nGenerating response...\n")
        response = self.generate_response(question, relevant_docs)
        
        return {
            'query': question,
            'retrieved_docs': relevant_docs,
            'response': response
        }
    
    def get_stats(self):
        """Get statistics about the indexed data"""
        return {
            'total_documents': len(self.documents),
            'collection_count': self.collection.count(),
            'storage_path': str(self.persist_dir)
        }


def main():
    """Main function to demonstrate the RAG system"""
    
    # Get Groq API key from environment variable
    groq_api_key = os.getenv('GROQ_RAG_API_KEY')
    if not groq_api_key:
        print("Error: Please set GROQ_API_KEY environment variable")
        print("Get your API key from: https://console.groq.com/keys")
        print("\nOn Linux/Mac: export GROQ_API_KEY='your-api-key'")
        print("On Windows: set GROQ_API_KEY=your-api-key")
        return
    
    # Initialize RAG system
    print("="*80)
    print("MEDICAL/BOOK RAG SYSTEM - PERSISTENT STORAGE")
    print("="*80)
    
    rag_system = MedicalRAGSystem(groq_api_key=groq_api_key)
    
    # Check if data already exists
    stats = rag_system.get_stats()
    
    if stats['total_documents'] > 0:
        print(f"\nFound existing index with {stats['total_documents']} documents")
        print(f"Storage location: {stats['storage_path']}")
        
        choice = input("\nDo you want to:\n1. Use existing index\n2. Process new book (will replace existing)\n\nChoice (1/2): ").strip()
        
        if choice == '2':
            book_path = input("\nEnter the path to your book/text file: ").strip()
            if os.path.exists(book_path):
                chunk_size = input("Enter chunk size (default 1000): ").strip()
                chunk_size = int(chunk_size) if chunk_size else 1000
                
                overlap = input("Enter overlap size (default 200): ").strip()
                overlap = int(overlap) if overlap else 200
                
                rag_system.process_book(book_path, chunk_size=chunk_size, overlap=overlap)
            else:
                print(f"File not found: {book_path}")
                return
    else:
        print("\nNo existing index found. Please process a book first.")
        book_path = input("Enter the path to your book/text file: ").strip()
        
        if not os.path.exists(book_path):
            print(f"File not found: {book_path}")
            print("\nExample: /path/to/medical_book.txt")
            return
        
        chunk_size = input("Enter chunk size (default 1000 words): ").strip()
        chunk_size = int(chunk_size) if chunk_size else 1000
        
        overlap = input("Enter overlap size (default 200 words): ").strip()
        overlap = int(overlap) if overlap else 200
        
        rag_system.process_book(book_path, chunk_size=chunk_size, overlap=overlap)
    
    # Interactive query mode
    print("\n" + "="*80)
    print("INTERACTIVE QUERY MODE")
    print("="*80)
    print("Ask questions about the book. Type 'stats' for statistics, 'exit' to quit.")
    print("="*80 + "\n")
    
    while True:
        user_query = input("\nYour question: ").strip()
        
        if user_query.lower() in ['exit', 'quit', 'q']:
            print("Goodbye!")
            break
        
        if user_query.lower() == 'stats':
            stats = rag_system.get_stats()
            print(f"\nSystem Statistics:")
            print(f"- Total documents: {stats['total_documents']}")
            print(f"- ChromaDB documents: {stats['collection_count']}")
            print(f"- Storage path: {stats['storage_path']}")
            continue
        
        if user_query:
            result = rag_system.query(user_query, search_type="hybrid", top_k=5)
            print("\n" + "-"*80)
            print("RESPONSE:")
            print("-"*80)
            print(result['response'])
            print("\n" + "="*80)


if __name__ == "__main__":
    main()