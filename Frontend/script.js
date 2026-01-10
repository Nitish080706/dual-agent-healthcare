const API_BASE_URL = 'http://localhost:5000/api';

let patientChart1 = null;
let patientChart2 = null;
let clinicChart1 = null;
let clinicChart2 = null;
let currentPatientData = null;
let currentClinicData = null;

function showSelectionPage() {
    document.getElementById('selectionPage').classList.add('active');
    document.getElementById('patientPage').classList.remove('active');
    document.getElementById('clinicPage').classList.remove('active');
}

function showPatientPage() {
    document.getElementById('selectionPage').classList.remove('active');
    document.getElementById('patientPage').classList.add('active');
    document.getElementById('clinicPage').classList.remove('active');

    resetPatientPage();
}

function showClinicPage() {
    document.getElementById('selectionPage').classList.remove('active');
    document.getElementById('patientPage').classList.remove('active');
    document.getElementById('clinicPage').classList.add('active');

    resetClinicPage();
}

async function handlePatientUpload(event) {
    const file = event.target.files[0];
    if (file) {
        showLoadingState('patient');

        try {
            const result = await uploadAndProcessFile(file, 'patient');
            currentPatientData = result.patientData;

            displayPatientResults();
        } catch (error) {
            console.error('Error processing file:', error);
            showErrorState('patient', error.message || 'Failed to process report');
        }
    }
}

function displayPatientResults() {
    document.getElementById('patientUploadSection').style.display = 'none';

    const resultsSection = document.getElementById('patientResultsSection');
    resultsSection.style.display = 'block';

    populatePatientDetails();

    createPatientCharts();
}

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

    if (patientChart1) {
        patientChart1.destroy();
    }
    if (patientChart2) {
        patientChart2.destroy();
    }

    const chartData = currentPatientData?.chartData;

    if (chartData && chartData.health_progression) {
        console.log('✅ Using visualization agent data');

        const ctx1 = document.getElementById('patientChart1').getContext('2d');
        const healthProg = chartData.health_progression;

        patientChart1 = new Chart(ctx1, {
            type: 'line',
            data: {
                labels: healthProg.labels,
                datasets: [{
                    label: 'Health Status Score',
                    data: healthProg.scores,
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
                                return 'Health Score: ' + context.parsed.y + '/100';
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

        const ctx2 = document.getElementById('patientChart2').getContext('2d');
        const labComp = chartData.lab_comparison;

        const testLabels = labComp.map(t => t.test_name);
        const testValues = labComp.map(t => t.value);

        patientChart2 = new Chart(ctx2, {
            type: 'bar',
            data: {
                labels: testLabels,
                datasets: [{
                    label: 'Current Values',
                    data: testValues,
                    backgroundColor: '#60A5FA',
                    borderColor: '#60A5FA',
                    borderWidth: 0,
                    borderRadius: 6
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
                            font: {
                                size: 11
                            }
                        }
                    },
                    tooltip: {
                        callbacks: {
                            label: function (context) {
                                const index = context.dataIndex;
                                const test = labComp[index];
                                return test.display_value;
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

        console.log('✅ Patient charts created successfully from agent data');
    } else {
        console.warn('⚠️ No chart data from visualization agent, using fallback');
        createPatientChartsFallback();
    }
}

function createPatientChartsFallback() {
    console.log('📊 Using fallback patient charts with sample data');

    const ctx1 = document.getElementById('patientChart1').getContext('2d');
    const ctx2 = document.getElementById('patientChart2').getContext('2d');

    patientChart1 = new Chart(ctx1, {
        type: 'line',
        data: {
            labels: ['Previous', 'Current', 'Target'],
            datasets: [{
                label: 'Health Score',
                data: [65, 75, 90],
                borderColor: '#60A5FA',
                backgroundColor: 'rgba(96, 165, 250, 0.1)',
                tension: 0.4,
                fill: true
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: true
        }
    });

    patientChart2 = new Chart(ctx2, {
        type: 'bar',
        data: {
            labels: ['Hemoglobin', 'WBC', 'RBC', 'Platelets'],
            datasets: [{
                label: 'Sample Data',
                data: [13.5, 7.2, 4.8, 250],
                backgroundColor: '#9CA3AF'
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: true
        }
    });
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

async function handleClinicUpload(event) {
    const file = event.target.files[0];
    if (file) {
        showLoadingState('clinic');

        try {
            const result = await uploadAndProcessFile(file, 'clinic');
            currentClinicData = result.clinicData;

            displayClinicResults();
        } catch (error) {
            console.error('Error processing file:', error);
            showErrorState('clinic', error.message || 'Failed to process report');
        }
    }
}

function displayClinicResults() {
    document.getElementById('clinicUploadSection').style.display = 'none';

    const resultsSection = document.getElementById('clinicResultsSection');
    resultsSection.style.display = 'block';

    populateClinicMetrics();

    populateClinicDetails();

}

function createClinicCharts() {
    console.log('🔷 createClinicCharts called');
    console.log('📊 Clinic Data:', currentClinicData);

    if (clinicChart1) {
        clinicChart1.destroy();
    }
    if (clinicChart2) {
        clinicChart2.destroy();
    }

    const chartData = currentClinicData?.chartData;

    if (chartData && chartData.lab_overview && chartData.reference_comparison) {
        console.log('✅ Using visualization agent data for clinic charts');

        const ctx1 = document.getElementById('clinicChart1');
        if (!ctx1) {
            console.error('❌ Chart canvas element clinicChart1 not found');
            return;
        }

        const labOverview = chartData.lab_overview;
        const labels1 = labOverview.map(t => t.test_name);
        const values1 = labOverview.map(t => t.value);

        clinicChart1 = new Chart(ctx1.getContext('2d'), {
            type: 'bar',
            data: {
                labels: labels1,
                datasets: [{
                    label: 'Test Values',
                    data: values1,
                    backgroundColor: '#60A5FA',
                    borderColor: '#3B82F6',
                    borderWidth: 0,
                    borderRadius: 6
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: true,
                plugins: {
                    legend: {
                        display: true,
                        labels: {
                            font: {
                                size: 11
                            }
                        }
                    },
                    tooltip: {
                        callbacks: {
                            label: function (context) {
                                const index = context.dataIndex;
                                const test = labOverview[index];
                                return test.display_value;
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

        console.log('✅ Clinic Chart 1 created from agent data');

        const ctx2 = document.getElementById('clinicChart2');
        if (!ctx2) {
            console.error('❌ Chart canvas element clinicChart2 not found');
            return;
        }

        const refComparison = chartData.reference_comparison;
        const labels2 = refComparison.map(t => t.test_name);
        const values2 = refComparison.map(t => t.value);

        const backgroundColors = refComparison.map(t => {
            switch (t.status) {
                case 'high': return '#F87171';
                case 'low': return '#FBBF24';
                default: return '#60A5FA';
            }
        });

        clinicChart2 = new Chart(ctx2.getContext('2d'), {
            type: 'bar',
            data: {
                labels: labels2,
                datasets: [{
                    label: 'Current Value',
                    data: values2,
                    backgroundColor: backgroundColors,
                    borderRadius: 6
                }]
            },
            options: {
                indexAxis: 'y',
                responsive: true,
                maintainAspectRatio: true,
                plugins: {
                    legend: {
                        display: false
                    },
                    tooltip: {
                        callbacks: {
                            label: function (context) {
                                const index = context.dataIndex;
                                const test = refComparison[index];
                                const result = [
                                    `Value: ${test.display_value}`,
                                    `Reference: ${test.reference_range}`
                                ];
                                if (test.status !== 'normal') {
                                    result.push(`Status: ${test.status.toUpperCase()}`);
                                }
                                return result;
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

        console.log('✅ Clinic charts created successfully from agent data');
    } else {
        console.warn('⚠️ No chart data from visualization agent for clinic');
        createClinicChartsFallback();
    }
}

function createClinicChartsFallback() {
    console.log('📊 Using fallback clinic charts');

    const ctx1 = document.getElementById('clinicChart1');
    const ctx2 = document.getElementById('clinicChart2');

    if (!ctx1 || !ctx2) {
        console.error('❌ Chart canvas elements not found');
        return;
    }

    clinicChart1 = new Chart(ctx1.getContext('2d'), {
        type: 'bar',
        data: {
            labels: ['Hemoglobin', 'WBC', 'RBC', 'Platelets'],
            datasets: [{
                label: 'Sample Data',
                data: [14.2, 6.8, 5.1, 280],
                backgroundColor: '#9CA3AF'
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: true
        }
    });

    clinicChart2 = new Chart(ctx2.getContext('2d'), {
        type: 'bar',
        data: {
            labels: ['Hemoglobin', 'WBC', 'RBC'],
            datasets: [{
                label: 'Sample Data',
                data: [14.2, 6.8, 5.1],
                backgroundColor: '#9CA3AF'
            }]
        },
        options: {
            indexAxis: 'y',
            responsive: true,
            maintainAspectRatio: true
        }
    });
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

    metricsGrid.innerHTML = '';

    if (labResults.length === 0) {
        console.warn('⚠️ Lab results array is empty');
        metricsGrid.innerHTML = '<p style="grid-column: 1/-1; text-align: center; color: var(--text-secondary);">No lab results available</p>';
        return;
    }

    console.log('✅ Creating', labResults.length, 'metric boxes');

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

    if (clinicChart1) {
        clinicChart1.destroy();
        clinicChart1 = null;
    }
    if (clinicChart2) {
        clinicChart2.destroy();
        clinicChart2 = null;
    }
    const metrics = ['hemoglobin', 'wbc', 'rbc', 'platelets', 'hematocrit', 'mcv', 'mch', 'mchc'];
    metrics.forEach(metric => {
        document.getElementById(metric).textContent = '--';
    });
}
