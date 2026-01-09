// API Configuration
const API_BASE_URL = 'http://localhost:5000/api';

let patientChart1 = null;
let patientChart2 = null;
let clinicChart1 = null;
let clinicChart2 = null;
let currentPatientData = null;
let currentClinicData = null;

// Navigation Functions
function showSelectionPage() {
    document.getElementById('selectionPage').classList.add('active');
    document.getElementById('patientPage').classList.remove('active');
    document.getElementById('clinicPage').classList.remove('active');
}

function showPatientPage() {
    document.getElementById('selectionPage').classList.remove('active');
    document.getElementById('patientPage').classList.add('active');
    document.getElementById('clinicPage').classList.remove('active');

    // Reset patient page
    resetPatientPage();
}

function showClinicPage() {
    document.getElementById('selectionPage').classList.remove('active');
    document.getElementById('patientPage').classList.remove('active');
    document.getElementById('clinicPage').classList.add('active');

    // Reset clinic page
    resetClinicPage();
}

// Patient Page Functions
async function handlePatientUpload(event) {
    const file = event.target.files[0];
    if (file) {
        // Show loading state
        showLoadingState('patient');

        try {
            // Upload and process file
            const result = await uploadAndProcessFile(file, 'patient');
            currentPatientData = result.patientData;

            // Display results
            displayPatientResults();
        } catch (error) {
            console.error('Error processing file:', error);
            showErrorState('patient', error.message || 'Failed to process report');
        }
    }
}

function displayPatientResults() {
    // Hide upload section
    document.getElementById('patientUploadSection').style.display = 'none';

    // Show results section
    const resultsSection = document.getElementById('patientResultsSection');
    resultsSection.style.display = 'block';

    // Populate primary box with details
    populatePatientDetails();

    // Create charts
    createPatientCharts();
}

// API Upload Function
async function uploadAndProcessFile(file, reportType) {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('reportType', reportType);
    formData.append('userId', 'web_user_' + Date.now());

    console.log('🔷 Uploading file:', file.name, 'Type:', reportType);

    const response = await fetch(`${API_BASE_URL}/upload`, {
        method: 'POST',
        body: formData
    });

    console.log('🔷 Response status:', response.status);

    if (!response.ok) {
        const error = await response.json();
        console.error('❌ Upload failed:', error);
        throw new Error(error.error || 'Upload failed');
    }

    const result = await response.json();
    console.log('✅ API Response:', result);
    console.log('📊 Lab Results:', result.clinicData?.labResults || result.patientData?.testResults);

    return result;
}

// Loading State Functions
function showLoadingState(pageType) {
    const uploadSection = document.getElementById(pageType + 'UploadSection');
    const resultsSection = document.getElementById(pageType + 'ResultsSection');

    uploadSection.style.display = 'none';
    resultsSection.style.display = 'block';

    const message = pageType === 'patient' ? 'patientDetails' : 'clinicDetails';
    document.getElementById(message).innerHTML = `
        <div style="text-align: center; padding: 40px;">
            <div class="loading-spinner"></div>
            <h3>Processing your report...</h3>
            <p>This may take a few moments. Please wait.</p>
        </div>
    `;
}

function showErrorState(pageType, errorMessage) {
    const message = pageType === 'patient' ? 'patientDetails' : 'clinicDetails';
    document.getElementById(message).innerHTML = `
        <div style="text-align: center; padding: 40px; color: #EF4444;">
            <h3>Error Processing Report</h3>
            <p>${errorMessage}</p>
            <button class="upload-btn" onclick="${pageType === 'patient' ? 'resetPatientPage' : 'resetClinicPage'}()">Try Again</button>
        </div>
    `;
}

function getHealthColor(health) {
    const colors = {
        'Excellent': '#10B981',
        'Good': '#3B82F6',
        'Moderate': '#F59E0B',
        'Danger': '#EF4444',
        'Unknown': '#6B7280'
    };
    return colors[health] || colors['Unknown'];
}

function populatePatientDetails() {
    const detailsContent = document.getElementById('patientDetails');

    if (!currentPatientData) {
        detailsContent.innerHTML = '<p>No data available</p>';
        return;
    }

    const patientInfo = currentPatientData.patientInfo || {};
    const abnormalities = currentPatientData.abnormalities || [];
    const summary = currentPatientData.summary || currentPatientData.patientExplanation || 'No summary available';
    const overallHealth = currentPatientData.overallHealth || 'Unknown';

    // Format abnormalities for display
    const abnormalitiesList = abnormalities.map(abn => {
        return `${abn.test || 'Unknown Test'}: ${abn.value || 'N/A'} ${abn.unit || ''} - ${abn.implication || abn.status || 'See doctor'}`;
    });

    detailsContent.innerHTML = `
        <h3>Patient Information</h3>
        <p><strong>Name:</strong> ${patientInfo.name || 'Not provided'}</p>
        <p><strong>Age:</strong> ${patientInfo.age || 'Not provided'}</p>
        <p><strong>Sex:</strong> ${patientInfo.sex || 'Not provided'}</p>
        <p><strong>Overall Health:</strong> <span style="color: ${getHealthColor(overallHealth)}; font-weight: bold;">${overallHealth}</span></p>
        
        <h3>Summary</h3>
        <p>${summary}</p>
        
        ${abnormalitiesList.length > 0 ? `
        <div class="abnormalities-list">
            <h4>Abnormalities Detected</h4>
            <ul>
                ${abnormalitiesList.map(item => `<li>${item}</li>`).join('')}
            </ul>
        </div>
        ` : '<p><em>No significant abnormalities detected</em></p>'}
    `;
}

function createPatientCharts() {
    console.log('🔷 createPatientCharts called');
    console.log('📊 Patient Data:', currentPatientData);

    // Destroy existing charts if they exist
    if (patientChart1) {
        patientChart1.destroy();
    }
    if (patientChart2) {
        patientChart2.destroy();
    }

    // Use real data if available, otherwise use sample data
    let testResults = [];
    let overallHealth = 'Unknown';
    let usingSampleData = false;

    if (currentPatientData && currentPatientData.testResults && currentPatientData.testResults.length > 0) {
        testResults = currentPatientData.testResults;
        overallHealth = currentPatientData.overallHealth || 'Unknown';
        console.log('✅ Using real test results:', testResults.length);
    } else if (currentPatientData && currentPatientData.abnormalities && currentPatientData.abnormalities.length > 0) {
        testResults = currentPatientData.abnormalities;
        overallHealth = currentPatientData.overallHealth || 'Unknown';
        console.log('✅ Using abnormalities data:', testResults.length);
    } else {
        // Fallback to sample data
        usingSampleData = true;
        testResults = [
            { test_name: 'Hemoglobin', value: '13.5', unit: 'g/dL' },
            { test_name: 'WBC', value: '7.2', unit: '×10³/μL' },
            { test_name: 'RBC', value: '4.8', unit: '×10⁶/μL' },
            { test_name: 'Platelets', value: '250', unit: '×10³/μL' },
            { test_name: 'Hematocrit', value: '42', unit: '%' }
        ];
        overallHealth = 'Good';
        console.warn('⚠️ No patient data available, using sample data');
    }

    console.log('📊 Test Results:', testResults.length, testResults);
    console.log('🏥 Overall Health:', overallHealth);


    // Chart 1: Health Progression Timeline (Linear)
    const ctx1 = document.getElementById('patientChart1').getContext('2d');

    // Map health status to numeric score for timeline
    const healthScoreMap = {
        'Excellent': 100,
        'Good': 75,
        'Moderate': 50,
        'Danger': 25,
        'Unknown': 0
    };

    const healthScore = healthScoreMap[overallHealth] || 0;

    // Create progression data (simulated timeline - in real app, would use historical data)
    const timelineData = [
        { label: 'Previous', score: Math.max(0, healthScore - 10) },
        { label: 'Current', score: healthScore },
        { label: 'Target', score: Math.min(100, healthScore + 15) }
    ];

    patientChart1 = new Chart(ctx1, {
        type: 'line',
        data: {
            labels: timelineData.map(d => d.label),
            datasets: [{
                label: 'Health Status Score',
                data: timelineData.map(d => d.score),
                borderColor: '#60A5FA',
                backgroundColor: 'rgba(96, 165, 250, 0.1)',
                tension: 0.4,
                fill: true,
                borderWidth: 3,
                pointRadius: 6,
                pointHoverRadius: 8,
                pointBackgroundColor: '#60A5FA',
                pointBorderColor: '#ffffff',
                pointBorderWidth: 2
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: true,
            plugins: {
                legend: {
                    display: true,
                    position: 'top',
                    labels: {
                        usePointStyle: true,
                        padding: 15,
                        font: {
                            size: 12,
                            weight: '500'
                        }
                    }
                },
                tooltip: {
                    callbacks: {
                        label: function (context) {
                            let label = context.dataset.label || '';
                            if (label) {
                                label += ': ';
                            }
                            label += context.parsed.y + '/100';
                            return label;
                        }
                    }
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    max: 100,
                    grid: {
                        color: '#F3F4F6'
                    },
                    ticks: {
                        font: {
                            size: 11
                        },
                        color: '#6B7280',
                        callback: function (value) {
                            return value + '/100';
                        }
                    },
                    title: {
                        display: true,
                        text: 'Health Score',
                        font: {
                            size: 12,
                            weight: '600'
                        }
                    }
                },
                x: {
                    grid: {
                        display: false
                    },
                    ticks: {
                        font: {
                            size: 11,
                            weight: '500'
                        },
                        color: '#6B7280'
                    }
                }
            }
        }
    });

    // Chart 2: Lab Values Comparison (Bar)
    const ctx2 = document.getElementById('patientChart2').getContext('2d');

    console.log('📊 Creating Lab Values Comparison chart...');

    // Get test results - try multiple possible data sources
    let testsToDisplay = [];

    if (testResults && testResults.length > 0) {
        testsToDisplay = testResults.slice(0, 6);
    } else if (currentPatientData.abnormalities && currentPatientData.abnormalities.length > 0) {
        // Fallback to abnormalities if test results not available
        testsToDisplay = currentPatientData.abnormalities.slice(0, 6);
    } else if (usingSampleData) {
        // If using sample data, ensure testsToDisplay is populated from the sample data
        testsToDisplay = [
            { test_name: 'Hemoglobin', value: '13.5', unit: 'g/dL' },
            { test_name: 'WBC', value: '7.2', unit: '×10³/μL' },
            { test_name: 'RBC', value: '4.8', unit: '×10⁶/μL' },
            { test_name: 'Platelets', value: '250', unit: '×10³/μL' },
            { test_name: 'Hematocrit', value: '42', unit: '%' },
            { test_name: 'Glucose', value: '95', unit: 'mg/dL' }
        ].slice(0, 6);
    }


    console.log('📊 Tests to display:', testsToDisplay.length, testsToDisplay);

    // Always ensure the chart canvas is visible, even if no data (it will show empty chart or sample data)
    document.getElementById('patientChart2').style.display = 'block';

    const testLabels = testsToDisplay.map(t => t.test_name || t.test || 'Unknown Test');
    const testValues = testsToDisplay.map(t => {
        const val = parseFloat(t.value);
        return isNaN(val) ? 0 : val;
    });

    console.log('📊 Chart labels:', testLabels);
    console.log('📊 Chart values:', testValues);

    patientChart2 = new Chart(ctx2, {
        type: 'bar',
        data: {
            labels: testLabels,
            datasets: [{
                label: usingSampleData ? 'Sample Values (Upload report for real data)' : 'Current Values',
                data: testValues,
                backgroundColor: usingSampleData ? '#9CA3AF' : '#60A5FA',
                borderColor: usingSampleData ? '#6B7280' : '#60A5FA',
                borderWidth: 0,
                borderRadius: 6
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: true,
            plugins: {
                legend: {
                    display: usingSampleData,
                    position: 'top',
                    labels: {
                        font: {
                            size: 11,
                            style: 'italic'
                        },
                        color: '#6B7280'
                    }
                },
                tooltip: {
                    callbacks: {
                        label: function (context) {
                            const index = context.dataIndex;
                            const test = testsToDisplay[index];
                            return (test.value || context.parsed.y) + ' ' + (test.unit || '');
                        }
                    }
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    grid: {
                        color: '#F3F4F6'
                    },
                    ticks: {
                        font: {
                            size: 11
                        },
                        color: '#6B7280'
                    }
                },
                x: {
                    grid: {
                        display: false
                    },
                    ticks: {
                        font: {
                            size: 10
                        },
                        color: '#6B7280',
                        maxRotation: 45,
                        minRotation: 45
                    }
                }
            }
        }
    });

    console.log('✅ Patient charts created successfully');
}

function resetPatientPage() {
    document.getElementById('patientUploadSection').style.display = 'flex';
    document.getElementById('patientResultsSection').style.display = 'none';
    document.getElementById('patientFileInput').value = '';
    if (patientChart1) {
        patientChart1.destroy();
        patientChart1 = null;
    }
    if (patientChart2) {
        patientChart2.destroy();
        patientChart2 = null;
    }
}

// Clinic Page Functions
async function handleClinicUpload(event) {
    const file = event.target.files[0];
    if (file) {
        // Show loading state
        showLoadingState('clinic');

        try {
            // Upload and process file
            const result = await uploadAndProcessFile(file, 'clinic');
            currentClinicData = result.clinicData;

            // Display results
            displayClinicResults();
        } catch (error) {
            console.error('Error processing file:', error);
            showErrorState('clinic', error.message || 'Failed to process report');
        }
    }
}

function displayClinicResults() {
    // Hide upload section
    document.getElementById('clinicUploadSection').style.display = 'none';

    // Show results section
    const resultsSection = document.getElementById('clinicResultsSection');
    resultsSection.style.display = 'block';

    // Populate metrics
    populateClinicMetrics();

    // Populate additional details
    populateClinicDetails();

    // Create charts
    createClinicCharts();
}

function createClinicCharts() {
    console.log('🔷 createClinicCharts called');
    console.log('📊 Clinic Data:', currentClinicData);

    // Destroy existing charts if they exist
    if (clinicChart1) {
        clinicChart1.destroy();
    }
    if (clinicChart2) {
        clinicChart2.destroy();
    }

    // Use real data if available, otherwise use sample data
    let labResults = [];
    let usingSampleData = false;

    if (currentClinicData && currentClinicData.labResults && currentClinicData.labResults.length > 0) {
        labResults = currentClinicData.labResults;
        console.log('✅ Using real lab results:', labResults.length);
    } else {
        // Fallback to sample data
        usingSampleData = true;
        labResults = [
            { test_name: 'Hemoglobin', value: '14.2', unit: 'g/dL', ref_range: '13.5-17.5 g/dL' },
            { test_name: 'WBC', value: '6.8', unit: '×10³/μL', ref_range: '4.5-11.0 ×10³/μL' },
            { test_name: 'RBC', value: '5.1', unit: '×10⁶/μL', ref_range: '4.5-5.5 ×10⁶/μL' },
            { test_name: 'Platelets', value: '280', unit: '×10³/μL', ref_range: '150-400 ×10³/μL' },
            { test_name: 'Hematocrit', value: '44', unit: '%', ref_range: '40-52%' },
            { test_name: 'MCV', value: '88', unit: 'fL', ref_range: '80-100 fL' },
            { test_name: 'MCH', value: '29', unit: 'pg', ref_range: '27-33 pg' },
            { test_name: 'MCHC', value: '33', unit: 'g/dL', ref_range: '32-36 g/dL' }
        ];
        console.warn('⚠️ No clinic data available, using sample data');
    }

    console.log('📊 Lab Results for charts:', labResults.length, labResults);

    // Chart 1: Lab Values Overview (Bar chart)
    const ctx1 = document.getElementById('clinicChart1');
    if (!ctx1) {
        console.error('❌ Chart canvas element clinicChart1 not found');
        return;
    }

    console.log('✅ Creating Clinic Chart 1 (Lab Values Overview)');

    const labels = labResults.slice(0, 8).map(t => t.test_name || 'Unknown');
    const values = labResults.slice(0, 8).map(t => {
        const val = parseFloat(t.value);
        return isNaN(val) ? 0 : val;
    });

    console.log('📊 Chart 1 Labels:', labels);
    console.log('📊 Chart 1 Values:', values);

    clinicChart1 = new Chart(ctx1.getContext('2d'), {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [{
                label: usingSampleData ? 'Sample Data' : 'Test Values',
                data: values,
                backgroundColor: usingSampleData ? '#9CA3AF' : '#60A5FA',
                borderColor: usingSampleData ? '#6B7280' : '#3B82F6',
                borderWidth: 1,
                borderRadius: 6
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: true,
            plugins: {
                legend: {
                    display: usingSampleData,
                    labels: {
                        font: {
                            size: 11,
                            style: 'italic'
                        },
                        color: '#6B7280'
                    }
                },
                tooltip: {
                    callbacks: {
                        label: function (context) {
                            const index = context.dataIndex;
                            const test = labResults[index];
                            return `${test.value} ${test.unit || ''}`;
                        }
                    }
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    grid: {
                        color: '#F3F4F6'
                    },
                    ticks: {
                        font: {
                            size: 11
                        },
                        color: '#6B7280'
                    }
                },
                x: {
                    grid: {
                        display: false
                    },
                    ticks: {
                        font: {
                            size: 10
                        },
                        color: '#6B7280',
                        maxRotation: 45,
                        minRotation: 45
                    }
                }
            }
        }
    });

    console.log('✅ Clinic Chart 1 created');

    // Chart 2: Values vs Reference Ranges (Horizontal Bar for better comparison)
    const ctx2 = document.getElementById('clinicChart2');
    if (!ctx2) {
        console.error('❌ Chart canvas element clinicChart2 not found');
        return;
    }

    console.log('✅ Creating Clinic Chart 2 (Values vs Reference)');

    // Filter tests that have reference ranges
    const testsWithRanges = labResults.filter(t => t.ref_range || t.reference_range).slice(0, 6);

    console.log('📊 Tests with reference ranges:', testsWithRanges.length, testsWithRanges);

    // Always create chart 2, use available tests if no reference ranges
    const testsToUse = testsWithRanges.length > 0 ? testsWithRanges : labResults.slice(0, 6);
    const hasReferenceRanges = testsWithRanges.length > 0;

    const rangeLabels = testsToUse.map(t => t.test_name || 'Unknown');
    const rangeValues = testsToUse.map(t => {
        const val = parseFloat(t.value);
        return isNaN(val) ? 0 : val;
    });

    clinicChart2 = new Chart(ctx2.getContext('2d'), {
        type: 'bar',
        data: {
            labels: rangeLabels,
            datasets: [{
                label: usingSampleData ? 'Sample Data' : 'Current Value',
                data: rangeValues,
                backgroundColor: usingSampleData ? '#9CA3AF' : '#60A5FA',
                borderRadius: 6
            }]
        },
        options: {
            indexAxis: 'y',
            responsive: true,
            maintainAspectRatio: true,
            plugins: {
                legend: {
                    display: usingSampleData,
                    labels: {
                        font: {
                            size: 11,
                            style: 'italic'
                        },
                        color: '#6B7280'
                    }
                },
                tooltip: {
                    callbacks: {
                        label: function (context) {
                            const index = context.dataIndex;
                            const test = testsToUse[index];
                            const refRange = test.ref_range || test.reference_range;
                            if (refRange) {
                                return [
                                    `Value: ${test.value} ${test.unit || ''}`,
                                    `Reference: ${refRange}`
                                ];
                            }
                            return `Value: ${test.value} ${test.unit || ''}`;
                        }
                    }
                }
            },
            scales: {
                x: {
                    beginAtZero: true,
                    grid: {
                        color: '#F3F4F6'
                    },
                    ticks: {
                        font: {
                            size: 11
                        },
                        color: '#6B7280'
                    }
                },
                y: {
                    grid: {
                        display: false
                    },
                    ticks: {
                        font: {
                            size: 10
                        },
                        color: '#6B7280'
                    }
                }
            }
        }
    });

    console.log(`✅ Clinic Chart 2 created ${usingSampleData ? '(sample data)' : hasReferenceRanges ? '(with reference ranges)' : '(without reference ranges)'}`);
    console.log('✅ Clinic charts created successfully');
}

function populateClinicMetrics() {
    console.log('🔷 populateClinicMetrics called', currentClinicData);

    if (!currentClinicData || !currentClinicData.labResults) {
        console.warn('⚠️ No clinic data or lab results available');
        return;
    }

    const labResults = currentClinicData.labResults;
    console.log('📊 Lab Results count:', labResults.length, labResults);

    const metricsGrid = document.querySelector('.metrics-grid');

    if (!metricsGrid) {
        console.error('❌ Metrics grid element not found');
        return;
    }

    // Clear existing metrics
    metricsGrid.innerHTML = '';

    // If no lab results, show message
    if (labResults.length === 0) {
        console.warn('⚠️ Lab results array is empty');
        metricsGrid.innerHTML = '<p style="grid-column: 1/-1; text-align: center; color: var(--text-secondary);">No lab results available</p>';
        return;
    }

    console.log('✅ Creating', labResults.length, 'metric boxes');

    // Create metric box for each lab result
    labResults.forEach((test, index) => {
        console.log(`  Creating metric ${index + 1}:`, test);

        const metricBox = document.createElement('div');
        metricBox.className = 'metric-box';

        const testName = test.test_name || 'Unknown Test';
        const value = test.value || '--';
        const unit = test.unit || '';
        const refRange = test.ref_range || test.reference_range || '';

        metricBox.innerHTML = `
            <div class="metric-label">${testName}</div>
            <div class="metric-value">${value}</div>
            <div class="metric-unit">${unit}</div>
            ${refRange ? `<div class="metric-ref" style="font-size: 0.75rem; color: var(--text-secondary); margin-top: 4px;">Ref: ${refRange}</div>` : ''}
        `;

        metricsGrid.appendChild(metricBox);
    });

    console.log('✅ Metrics populated successfully');
}

function populateClinicDetails() {
    const detailsContent = document.getElementById('clinicDetails');

    if (!currentClinicData) {
        detailsContent.innerHTML = '<p>No data available</p>';
        return;
    }

    const patientInfo = currentClinicData.patientInfo || {};
    const clinicalNotes = currentClinicData.clinicalNotes || currentClinicData.clinicianSummary || 'No clinical notes available';
    const overallHealth = currentClinicData.overallHealth || 'Unknown';
    const evidenceSources = currentClinicData.evidenceSources || [];
    const criticalFindings = currentClinicData.criticalFindings || [];
    const normalFindings = currentClinicData.normalFindings || [];
    const recommendations = currentClinicData.recommendations || [];
    const differentialConsiderations = currentClinicData.differentialConsiderations || [];

    // Format evidence sources
    const evidenceList = evidenceSources.slice(0, 5).map(source => `<li style="padding: 8px 0; border-bottom: 1px solid #E5E7EB; color: #6B7280;"><a href="${source}" target="_blank" style="color: #3B82F6; text-decoration: none;">${source}</a></li>`).join('');

    detailsContent.innerHTML = `
        <h3>Report Information</h3>
        <p><strong>Patient Name:</strong> ${patientInfo.name || 'Not provided'}</p>
        <p><strong>Age:</strong> ${patientInfo.age || 'Not provided'}</p>
        <p><strong>Sex:</strong> ${patientInfo.sex || 'Not provided'}</p>
        <p><strong>Overall Health Status:</strong> <span style="color: ${getHealthColor(overallHealth)}; font-weight: bold;">${overallHealth}</span></p>
        
        <h3>Clinical Summary</h3>
        <p style="white-space: pre-wrap;">${clinicalNotes}</p>
        
        ${criticalFindings.length > 0 ? `
        <h3>Critical Findings</h3>
        <ul style="list-style: none; padding-left: 0;">
            ${criticalFindings.map(finding => `
                <li style="padding: 12px; margin-bottom: 8px; background: #FEF2F2; border-left: 3px solid #EF4444; border-radius: 4px;">
                    <strong>${finding.test || 'Unknown Test'}:</strong> ${finding.value || 'N/A'} ${finding.unit || ''}<br>
                    <span style="color: #DC2626; font-weight: 500;">${finding.status || 'Abnormal'}</span><br>
                    <small style="color: #6B7280;">Reference: ${finding.reference_range || 'N/A'}</small><br>
                    <small>${finding.clinical_significance || ''}</small>
                    ${finding.evidence ? `<br><small style="color: #3B82F6;">Evidence: ${finding.evidence}</small>` : ''}
                </li>
            `).join('')}
        </ul>
        ` : ''}
        
        ${normalFindings.length > 0 ? `
        <h3>Normal Findings</h3>
        <p style="color: #10B981;">${normalFindings.join(', ')}</p>
        ` : ''}
        
        ${recommendations.length > 0 ? `
        <h3>Clinical Recommendations</h3>
        <ul style="list-style: disc; padding-left: 20px;">
            ${recommendations.map(rec => `<li style="margin-bottom: 8px; color: #6B7280;">${rec}</li>`).join('')}
        </ul>
        ` : ''}
        
        ${differentialConsiderations.length > 0 ? `
        <h3>Differential Considerations</h3>
        <ul style="list-style: circle; padding-left: 20px;">
            ${differentialConsiderations.map(diff => `<li style="margin-bottom: 4px; color: #6B7280;">${diff}</li>`).join('')}
        </ul>
        ` : ''}
        
        ${evidenceList ? `
        <h3>Evidence Sources</h3>
        <ul style="list-style: none; padding-left: 0;">
            ${evidenceList}
        </ul>
        ` : ''}
    `;
}

function resetClinicPage() {
    document.getElementById('clinicUploadSection').style.display = 'flex';
    document.getElementById('clinicResultsSection').style.display = 'none';
    document.getElementById('clinicFileInput').value = '';

    // Destroy charts
    if (clinicChart1) {
        clinicChart1.destroy();
        clinicChart1 = null;
    }
    if (clinicChart2) {
        clinicChart2.destroy();
        clinicChart2 = null;
    }
    // Reset metric values
    const metrics = ['hemoglobin', 'wbc', 'rbc', 'platelets', 'hematocrit', 'mcv', 'mch', 'mchc'];
    metrics.forEach(metric => {
        document.getElementById(metric).textContent = '--';
    });
}
