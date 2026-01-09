import os
import json
from flask import Flask, request, jsonify
from flask_cors import CORS
from werkzeug.utils import secure_filename
from pathlib import Path
import tempfile
import traceback

from extractor_summarize_3 import LabReportProcessor, MongoDBHandler
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

# Configuration
UPLOAD_FOLDER = tempfile.gettempdir()
ALLOWED_EXTENSIONS = {'pdf', 'png', 'jpg', 'jpeg', 'bmp'}
MAX_FILE_SIZE = 16 * 1024 * 1024  # 16MB

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = MAX_FILE_SIZE

# Initialize processor globally (reuse across requests)
processor = None
db_handler = None


def allowed_file(filename):
    """Check if file extension is allowed"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def initialize_processor():
    """Initialize the lab report processor"""
    global processor, db_handler
    if processor is None:
        try:
            print("Initializing LabReportProcessor...")
            processor = LabReportProcessor()
            print("LabReportProcessor initialized successfully")
            
            # Initialize MongoDB handler if URI is available
            mongodb_uri = os.getenv("MONGODB_URI")
            if mongodb_uri:
                try:
                    db_handler = MongoDBHandler(mongodb_uri)
                    print("MongoDB handler initialized successfully")
                except Exception as e:
                    print(f"MongoDB initialization failed: {e}")
                    db_handler = None
        except Exception as e:
            print(f"Failed to initialize processor: {e}")
            raise e


@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'message': 'Medical Report Analyzer API is running',
        'processor_initialized': processor is not None,
        'mongodb_connected': db_handler is not None
    }), 200


@app.route('/api/upload', methods=['POST'])
def upload_file():
    """
    Upload and process medical report
    Expected form data:
    - file: The medical report file (PDF or image)
    - reportType: 'patient' or 'clinic'
    - userId: Optional user identifier
    """
    try:
        # Initialize processor if not already done
        initialize_processor()
        
        # Check if file is present
        if 'file' not in request.files:
            return jsonify({'error': 'No file provided'}), 400
        
        file = request.files['file']
        
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        if not allowed_file(file.filename):
            return jsonify({'error': 'Invalid file type. Allowed: PDF, PNG, JPG, JPEG, BMP'}), 400
        
        # Get report type (patient or clinic)
        report_type = request.form.get('reportType', 'patient')
        user_id = request.form.get('userId', 'anonymous_user')
        
        # Save file temporarily
        filename = secure_filename(file.filename)
        temp_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(temp_path)
        
        try:
            # Process the report
            print(f"Processing report: {filename} (type: {report_type})")
            result = processor.process_lab_report(temp_path)
            
            # Store in MongoDB if available
            report_id = None
            if db_handler:
                try:
                    report_id = db_handler.store_lab_report(
                        user_id=user_id,
                        processed_data=result,
                        file_name=filename
                    )
                    print(f"Report stored in MongoDB with ID: {report_id}")
                except Exception as e:
                    print(f"Failed to store in MongoDB: {e}")
            
            # Format response based on report type
            response_data = format_response(result, report_type, report_id)
            
            return jsonify(response_data), 200
            
        finally:
            # Clean up temporary file
            if os.path.exists(temp_path):
                os.remove(temp_path)
    
    except Exception as e:
        print(f"Error processing upload: {e}")
        traceback.print_exc()
        return jsonify({
            'error': 'Failed to process report',
            'details': str(e)
        }), 500


def format_response(result, report_type, report_id=None):
    """Format the processing result for frontend consumption"""
    
    # Extract structured data
    structured_data = result.get('structured_data', {})
    health_summary = result.get('health_summary', {})
    detailed_analysis = result.get('detailed_analysis', {})
    patient_summary = result.get('patient_summary', {})
    clinician_summary = result.get('clinician_summary', {})
    research_findings = result.get('research_findings', {})
    
    response = {
        'reportId': report_id,
        'reportType': report_type,
        'timestamp': str(Path().cwd()),  # Use for debugging
    }
    
    if report_type == 'patient':
        # Format for patient view
        response['patientData'] = {
            'patientInfo': structured_data.get('patient_demographics', {}),
            'summary': patient_summary.get('plain_language_summary', health_summary.get('summary_text', '')),
            'overallHealth': health_summary.get('overall_health_reading', 'Unknown'),
            'keyFindings': health_summary.get('key_findings', []),
            'abnormalities': detailed_analysis.get('abnormalities', []),
            'recommendations': detailed_analysis.get('lifestyle_recommendations', []),
            'testResults': structured_data.get('lab_results', []),
            'patientExplanation': patient_summary.get('plain_language_summary', research_findings.get('patient_explainer', '')),
            'needsAttention': patient_summary.get('needs_attention', []),
            'whatIsNormal': patient_summary.get('what_is_normal', []),
        }
    else:
        # Format for clinic view
        # Build comprehensive clinical notes from clinician summary
        clinical_notes_parts = []
        
        # Add clinical context
        if clinician_summary.get('clinical_context'):
            clinical_notes_parts.append(f"Clinical Context: {clinician_summary.get('clinical_context')}")
        
        # Add critical findings summary
        critical_findings = clinician_summary.get('critical_findings', [])
        if critical_findings:
            clinical_notes_parts.append(f"\nCritical Findings: {len(critical_findings)} abnormal value(s) detected")
        
        # Add differential considerations
        diff_considerations = clinician_summary.get('differential_considerations', [])
        if diff_considerations:
            clinical_notes_parts.append(f"\nDifferential Considerations: {', '.join(diff_considerations)}")
        
        # Add recommendations summary
        recommendations = clinician_summary.get('recommendations', [])
        if recommendations:
            clinical_notes_parts.append(f"\nRecommendations: {'; '.join(recommendations)}")
        
        # Fallback to research clinician summary if agent summary is empty
        clinical_notes = '\n'.join(clinical_notes_parts) if clinical_notes_parts else \
                        research_findings.get('clinician_summary', health_summary.get('summary_text', 'No clinical notes available'))
        
        response['clinicData'] = {
            'patientInfo': structured_data.get('patient_demographics', {}),
            'labResults': structured_data.get('lab_results', []),
            'summary': clinician_summary.get('clinical_context', health_summary.get('summary_text', '')),
            'overallHealth': health_summary.get('overall_health_reading', 'Unknown'),
            'abnormalities': detailed_analysis.get('abnormalities', []),
            'recommendations': clinician_summary.get('recommendations', detailed_analysis.get('lifestyle_recommendations', [])),
            'clinicalNotes': clinical_notes,
            'evidenceSources': clinician_summary.get('evidence_sources', research_findings.get('evidence_sources', [])),
            'clinicianSummary': research_findings.get('clinician_summary', ''),
            'criticalFindings': clinician_summary.get('critical_findings', []),
            'normalFindings': clinician_summary.get('normal_findings', []),
            'differentialConsiderations': clinician_summary.get('differential_considerations', []),
        }
    
    return response


@app.errorhandler(413)
def request_entity_too_large(error):
    """Handle file too large error"""
    return jsonify({'error': 'File too large. Maximum size is 16MB'}), 413


@app.errorhandler(500)
def internal_server_error(error):
    """Handle internal server errors"""
    return jsonify({'error': 'Internal server error', 'details': str(error)}), 500


if __name__ == '__main__':
    print("=" * 60)
    print("Medical Report Analyzer API")
    print("=" * 60)
    print("Initializing server...")
    
    try:
        initialize_processor()
        print("\nServer ready!")
        print("API Endpoints:")
        print("  GET  /api/health  - Health check")
        print("  POST /api/upload  - Upload and process medical report")
        print("\nStarting Flask server on http://localhost:5000")
        print("=" * 60)
        
        app.run(debug=True, host='0.0.0.0', port=5000)
    except Exception as e:
        print(f"\nFailed to start server: {e}")
        traceback.print_exc()
