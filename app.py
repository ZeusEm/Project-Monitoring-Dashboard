"""
ERP Monitoring Platform for Naval Dockyard (Mumbai)
Production-ready version with report enhancements
"""

# -*- coding: utf-8 -*-

from flask import Flask, request, jsonify, send_file
import sqlite3
from datetime import datetime
from datetime import date  # For isocalendar
from datetime import timedelta
from io import BytesIO
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Table, TableStyle, Spacer
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib import colors

# ========== CONFIGURATION ==========
SECRET_CODE = "CYERP"
PORT = 5000
DEBUG = False

app = Flask(__name__)

# ========== DATABASE ==========
def get_db_connection():
    conn = sqlite3.connect('erp_observations.db')
    conn.row_factory = sqlite3.Row
    return conn

def init_database():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.executescript("""
        CREATE TABLE IF NOT EXISTS module_groups (
            group_id INTEGER PRIMARY KEY AUTOINCREMENT,
            group_name TEXT UNIQUE NOT NULL
        );
        CREATE TABLE IF NOT EXISTS modules (
            module_id INTEGER PRIMARY KEY AUTOINCREMENT,
            module_name TEXT UNIQUE NOT NULL,
            group_id INTEGER NOT NULL,
            FOREIGN KEY (group_id) REFERENCES module_groups(group_id)
        );
        CREATE TABLE IF NOT EXISTS observations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            observation TEXT NOT NULL,
            module_id INTEGER NOT NULL,
            criticality TEXT NOT NULL,
            status TEXT DEFAULT 'OPEN',
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            closed_on DATETIME,
            resurfaced_on DATETIME,
            FOREIGN KEY (module_id) REFERENCES modules(module_id)
        );
    """)
    cursor.execute("INSERT OR IGNORE INTO module_groups (group_name) VALUES ('HR Modules'), ('Refit Modules'), ('Commercial Modules'), ('Services Modules')")
    modules_data = [
        ('Salary & Wages Module (SWM)', 1), ('Time Keeping System (TKS)', 1), ('Personnel Information Management System (PIMS)', 1),
        ('Refit Planning Process (RPP)', 2), ('Defect List (DL)', 2), ('Shop Floor Management Module (SFMM)', 2), ('Operational Defect Management (OPDEF)', 2),
        ('Operational Assistance (OPRA)', 2), ('Refit Monitoring Module (RMM)', 2), ('Operational Repair Monitoring (ORM)', 2), ('Quality Control Management System (QCMS)', 2),
        ('Manpower Booking (MPB)', 2), ('Dry Docking Module (DRY DOCK)', 2), ('Berthing Module (BERTHING)', 2),
        ('Financial Management Module (FMS), Budget Management Module (BMS), Local Procurement (LP) Module', 3), ('Vendor Management System (VMS)', 3),
        ('Yard Utility Services (YUS)', 4), ('Yard Security Module (YSM)', 4), ('Quality Assurance Module (QAM)', 4), ('Management Information Systems (MIS)', 4),
        ('E-Seva', 4), ('E-Samagri', 4), ('Medical & Health Management System (MHMS)', 4), ('Coster', 4), ('Yard Asset Management (YAMS)', 4)
    ]
    for name, gid in modules_data:
        cursor.execute("INSERT OR IGNORE INTO modules (module_name, group_id) VALUES (?, ?)", (name, gid))
    conn.commit()
    conn.close()
    print("Database initialized")

def week_label(year_week):
    """
    Convert a YYYY-WW string into a human-readable week range.
    Example: '2025-50' -> '08 Dec - 14 Dec'
    """
    year, week = map(int, year_week.split('-'))
    start = datetime.date.fromisocalendar(year, week, 1)  # Monday
    end = start + datetime.timedelta(days=6)
    return f"{start.strftime('%d %b')} - {end.strftime('%d %b')}"

# ========== HOMEPAGE ==========
@app.route('/')
def homepage():
    return '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Naval Dockyard (Mumbai) - Navyojana Monitoring Platform</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.0/font/bootstrap-icons.css">
    <style>
        :root { --navy-blue: #0a2463; --gold: #ffd700; }
        body { background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%); min-height: 100vh; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; }
        .navy-header { background: linear-gradient(135deg, var(--navy-blue) 0%, #1e3a8a 100%); border-bottom: 4px solid var(--gold); box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1); }
        .card-platform { border-radius: 15px; border: none; box-shadow: 0 5px 15px rgba(0, 0, 0, 0.08); transition: transform 0.3s; border-top: 4px solid var(--navy-blue); }
        .card-platform:hover { transform: translateY(-5px); box-shadow: 0 10px 25px rgba(0, 0, 0, 0.12); }
        .btn-action { padding: 2rem 1.5rem; border-radius: 10px; font-weight: 600; font-size: 1.1rem; }
        .btn-report { background: linear-gradient(135deg, #6c757d 0%, #495057 100%); color: white; }
        .btn-add { background: linear-gradient(135deg, #198754 0%, #146c43 100%); color: white; }
        .modal-navy .modal-header { background: var(--navy-blue); color: white; border-bottom: 3px solid var(--gold); }
        .footer-navy { background: var(--navy-blue); color: white; border-top: 3px solid var(--gold); margin-top: auto; }
        @media (max-width: 768px) { .btn-action { padding: 1.5rem 1rem; font-size: 1rem; } }
    </style>
<style>
.obs-vital td {
  background-color: #e51f1f !important;
  color: #fff;
}

.obs-essential td {
  background-color: #f2a134 !important;
}

.obs-desirable td {
  background-color: #f7e379 !important;
}

.obs-resurfaced td {
  background-color: #bbdb44 !important;
}

.obs-closed td {
  background-color: #44ce1b !important;
  color: #fff;
}
</style>
<style>
.obs-legend {
  display: flex;
  gap: 10px;
  font-size: 0.75rem;
  align-items: center;
}

.obs-legend span {
  display: flex;
  align-items: center;
  gap: 4px;
}

.legend-box {
  width: 12px;
  height: 12px;
  border-radius: 3px;
  display: inline-block;
}

.legend-vital { background-color: #e51f1f; }
.legend-essential { background-color: #f2a134; }
.legend-desirable { background-color: #f7e379; }
.legend-resurfaced { background-color: #bbdb44; }
.legend-closed { background-color: #44ce1b; }
</style>

<style>
.chart-container {
  position: relative;
  height: 220px;       /* desktop */
}

@media (max-width: 768px) {
  .chart-container {
    height: 180px;     /* mobile */
  }
}
</style>

</head>
<body class="d-flex flex-column min-vh-100">
    <header class="navy-header text-white py-4">
        <div class="container">
            <div class="row align-items-center">
                <div class="col-md-8">
                    <h1 class="display-5 fw-bold mb-2"><i class="bi bi-building"></i> Naval Dockyard (Mumbai)</h1>
                    <p class="lead mb-0 opacity-90"><i class="bi bi-speedometer2"></i> Navyojana Monitoring Platform</p>
                </div>
                <div class="col-md-4 text-md-end">
                    <div class="badge bg-warning text-dark p-2"><i class="bi bi-shield-check"></i> Secure Portal</div>
                </div>
            </div>
        </div>
    </header>
    <main class="flex-grow-1 py-5">
        <div class="container">
            <div class="card-platform mb-5 p-4">
                <div class="row align-items-center">
                    <div class="col-md-8">
                        <h3 class="mb-2"><i class="bi bi-clipboard-data text-primary"></i> ERP Monitoring Dashboard</h3>
                        <p class="text-muted mb-0">Monitor observations across all ERP modules. Add new observations or generate reports.</p>
                    </div>
                    <div class="col-md-4 text-md-end">
                        <span class="text-success fw-bold"><i class="bi bi-check-circle-fill"></i> Status: <span class="badge bg-success">Operational</span></span>
                    </div>
                </div>
            </div>
<div class="row mt-3">
  <div class="col-md-6 col-12 mb-3">
    <div class="card shadow-sm h-100">
      <div class="card-body">
        <h6 class="card-title text-center mb-3">Observations Trend (Criticality-wise)</h6>
        <div class="chart-container">
          <canvas id="criticalityTrendChart"></canvas>
        </div>
      </div>
    </div>
  </div>

  <div class="col-md-6 col-12 mb-3">
    <div class="card shadow-sm h-100">
      <div class="card-body">
        <h6 class="card-title text-center mb-3">Module Vital Trend</h6>
        <div class="chart-container">
          <canvas id="moduleVitalTrendChart"></canvas>
        </div>
      </div>
    </div>
  </div>
</div>

            <div class="row g-4 justify-content-center mb-5">
                <div class="col-xl-4 col-lg-5 col-md-6">
                    <div class="card-platform h-100">
                        <div class="card-body text-center p-4">
                            <div class="mb-3">
                                <div class="bg-light rounded-circle d-inline-flex p-3 mb-3"><i class="bi bi-graph-up-arrow text-muted fs-1"></i></div>
                                <h4 class="card-title mb-3">Generate Reports</h4>
                                <p class="card-text text-muted mb-4">Access comprehensive analytics and reports.</p>
                                <button class="btn btn-report btn-action w-100" data-bs-toggle="modal" data-bs-target="#reportModal"><i class="bi bi-graph-up me-2"></i> View Reports</button>
				<button class="btn btn-info btn-action w-100 mt-2" data-bs-toggle="modal" data-bs-target="#viewObservationsModal"><i class="bi bi-list-check me-2"></i> View Observations</button>
                            </div>
                        </div>
                    </div>
                </div>
                <div class="col-xl-4 col-lg-5 col-md-6">
                    <div class="card-platform h-100">
                        <div class="card-body text-center p-4">
                            <div class="mb-3">
                                <div class="bg-success bg-opacity-10 rounded-circle d-inline-flex p-3 mb-3"><i class="bi bi-plus-circle text-success fs-1"></i></div>
                                <h4 class="card-title mb-3">Add Observation</h4>
                                <p class="card-text text-muted mb-4">Submit new observations for any ERP module.</p>
                                <button class="btn btn-add btn-action w-100" data-bs-toggle="modal" data-bs-target="#observationModal"><i class="bi bi-plus-circle me-2"></i> Add New Observation</button>
                                <button class="btn btn-warning btn-action w-100 mt-2" data-bs-toggle="modal" data-bs-target="#resurfaceModal"><i class="bi bi-arrow-repeat me-2"></i> Mark Resurfaced</button>
                                <button class="btn btn-danger btn-action w-100 mt-2" data-bs-toggle="modal" data-bs-target="#closeModal"><i class="bi bi-x-circle me-2"></i> Close Observations</button>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
            <div class="card-platform p-4 mb-5">
                <div class="row text-center">
                    <div class="col-md-4 border-end py-3">
                        <h3 class="mb-1" id="totalObservations">0</h3>
                        <p class="text-muted mb-0">Total Pending Observations</p>
                    </div>
                    <div class="col-md-4 border-end py-3">
                        <h3 class="mb-1">4</h3>
                        <p class="text-muted mb-0">Module Groups</p>
                    </div>
                    <div class="col-md-4 py-3">
                        <h3 class="mb-1">25</h3>
                        <p class="text-muted mb-0">ERP Modules</p>
                    </div>
                </div>
            </div>
        </div>
    </main>
    <!-- Observation Modal -->
    <div class="modal fade modal-navy" id="observationModal" tabindex="-1">
        <div class="modal-dialog modal-lg">
            <div class="modal-content">
                <div class="modal-header">
                    <h5 class="modal-title"><i class="bi bi-clipboard-plus me-2"></i>Add New Observation</h5>
                    <button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal"></button>
                </div>
                <div class="modal-body p-4">
                    <form id="observationForm">
                        <div class="mb-4">
                            <label class="form-label fw-bold"><i class="bi bi-chat-left-text me-1"></i>Observation Details <span class="text-danger">*</span></label>
                            <textarea class="form-control" name="observation" rows="4" required></textarea>
                        </div>
                        <div class="mb-4">
                            <label class="form-label fw-bold"><i class="bi bi-grid-3x3-gap me-1"></i>ERP Module <span class="text-danger">*</span></label>
                            <select class="form-select" name="module_id" required>
                                <option value="">Select a module</option>
                                <optgroup label="HR Modules">
                                    <option value="1">Salary & Wages Module (SWM)</option>
                                    <option value="2">Time Keeping System (TKS)</option>
                                    <option value="3">Personnel Information Management System (PIMS)</option>
                                </optgroup>
                                <optgroup label="Refit Modules">
                                    <option value="4">Refit Planning Process (RPP)</option>
                                    <option value="5">Defect List (DL)</option>
                                    <option value="6">Shop Floor Management Module (SFMM)</option>
                                    <option value="7">Operational Defect Management (OPDEF)</option>
                                    <option value="8">Operational Assistance (OPRA)</option>
                                    <option value="9">Refit Monitoring Module (RMM)</option>
                                    <option value="10">Operational Repair Monitoring (ORM)</option>
                                    <option value="11">Quality Control Management System (QCMS)</option>
                                    <option value="12">Manpower Booking (MPB)</option>
                                    <option value="13">Dry Docking Module (DRY DOCK)</option>
                                    <option value="14">Berthing Module (BERTHING)</option>
                                </optgroup>
                                <optgroup label="Commercial Modules">
                                    <option value="15">Financial Management Module (FMS), Budget Management Module (BMS), Local Procurement (LP) Module</option>
                                    <option value="16">Vendor Management System (VMS)</option>
                                </optgroup>
                                <optgroup label="Services Modules">
                                    <option value="17">Yard Utility Services (YUS)</option>
                                    <option value="18">Yard Security Module (YSM)</option>
                                    <option value="19">Quality Assurance Module (QAM)</option>
                                    <option value="20">Management Information Systems (MIS)</option>
                                    <option value="21">E-Seva</option>
                                    <option value="22">E-Samagri</option>
                                    <option value="23">Medical & Health Management System (MHMS)</option>
                                    <option value="24">Coster</option>
                                    <option value="25">Yard Asset Management (YAMS)</option>
                                </optgroup>
                            </select>
                        </div>
                        <div class="mb-4">
                            <label class="form-label fw-bold"><i class="bi bi-exclamation-triangle me-1"></i>Criticality Level <span class="text-danger">*</span></label>
                            <select class="form-select" name="criticality" required>
                                <option value="">Select criticality</option>
                                <option value="Vital">Vital</option>
                                <option value="Essential">Essential</option>
                                <option value="Desirable">Desirable</option>
                            </select>
                        </div>
                        <div class="mb-4">
                            <label class="form-label fw-bold"><i class="bi bi-key me-1"></i>Authorization Code <span class="text-danger">*</span></label>
                            <input type="password" class="form-control" name="secret_code" required>
                            <small class="form-text text-muted"><i class="bi bi-info-circle"></i> Enter "CYERP" to submit</small>
                        </div>
                        <div class="alert alert-danger d-none" id="errorAlert"></div>
                        <div class="alert alert-success d-none" id="successAlert"><i class="bi bi-check-circle me-2"></i>Observation saved successfully!</div>
                    </form>
                </div>
                <div class="modal-footer">
                    <button type="button" class="btn btn-secondary" data-bs-dismiss="modal"><i class="bi bi-x-circle me-1"></i>Cancel</button>
                    <button type="button" class="btn btn-primary" onclick="saveObservation()"><i class="bi bi-cloud-upload me-1"></i>Save Observation</button>
                </div>
            </div>
        </div>
    </div>
    <!-- Resurface Modal -->
    <div class="modal fade modal-navy" id="resurfaceModal" tabindex="-1">
        <div class="modal-dialog modal-lg">
            <div class="modal-content">
                <div class="modal-header">
                    <h5 class="modal-title"><i class="bi bi-arrow-repeat me-2"></i>Resurface Observations</h5>
                    <button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal"></button>
                </div>
                <div class="modal-body p-4">
                    <div class="row mb-3">
                        <div class="col-md-6">
                            <label class="form-label fw-bold">Module Group</label>
                            <select class="form-select" id="resurfaceGroup"><option value="">Select Group</option></select>
                        </div>
                        <div class="col-md-6">
                            <label class="form-label fw-bold">Module</label>
                            <select class="form-select" id="resurfaceModule"><option value="">Select Module</option></select>
                        </div>
                    </div>
                    <div class="card mb-3">
                        <div class="card-header bg-warning bg-opacity-10"><i class="bi bi-exclamation-triangle text-warning me-2"></i>Select CLOSED observations to mark as RESURFACED</div>
                        <div class="card-body" id="resurfaceList" style="max-height: 300px; overflow-y: auto;"></div>
                    </div>
                    <button class="btn btn-warning mt-3" onclick="submitResurface()"><i class="bi bi-arrow-repeat me-2"></i> Mark as Resurfaced</button>
                </div>
            </div>
        </div>
    </div>
    <!-- Close Modal -->
    <div class="modal fade modal-navy" id="closeModal" tabindex="-1">
        <div class="modal-dialog modal-lg">
            <div class="modal-content">
                <div class="modal-header">
                    <h5 class="modal-title"><i class="bi bi-x-circle me-2"></i>Close Observations</h5>
                    <button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal"></button>
                </div>
                <div class="modal-body p-4">
                    <div class="row mb-3">
                        <div class="col-md-6">
                            <label class="form-label fw-bold">Module Group</label>
                            <select class="form-select" id="closeGroup"><option value="">Select Group</option></select>
                        </div>
                        <div class="col-md-6">
                            <label class="form-label fw-bold">Module</label>
                            <select class="form-select" id="closeModule"><option value="">Select Module</option></select>
                        </div>
                    </div>
                    <div class="card mb-3">
                        <div class="card-header bg-danger bg-opacity-10"><i class="bi bi-exclamation-triangle text-danger me-2"></i>Select OPEN/RESURFACED observations to CLOSE</div>
                        <div class="card-body" id="closeList" style="max-height: 300px; overflow-y: auto;"></div>
                    </div>
                    <button class="btn btn-danger mt-3" onclick="submitClose()"><i class="bi bi-check-circle me-2"></i> Mark Closed</button>
                </div>
            </div>
        </div>
    </div>
    <!-- Report Modal -->
    <div class="modal fade modal-navy" id="reportModal" tabindex="-1">
        <div class="modal-dialog modal-xl">
            <div class="modal-content">
                <div class="modal-header">
                    <h5 class="modal-title"><i class="bi bi-graph-up"></i> Generate Report</h5>
                    <button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal"></button>
                </div>
                <div class="modal-body">
                    <div class="row mb-3">
                        <div class="col-md-6">
                            <label class="form-label fw-bold">From Date</label>
                            <input type="date" class="form-control" id="reportFromDate">
                        </div>
                        <div class="col-md-6">
                            <label class="form-label fw-bold">To Date</label>
                            <input type="date" class="form-control" id="reportToDate">
                        </div>
                    </div>
                    <div class="text-end">
                        <button class="btn btn-primary" onclick="generateReport()">Generate</button>
                    </div>
                    <hr>
                    <div id="reportResult" class="d-none">
                        <h5 class="fw-bold mt-3">OVERALL PENDING VITAL OBSERVATIONS</h5>
                        <table class="table table-bordered mt-3">
                            <thead class="table-light">
                                <tr>
                                    <th>GROUP</th>
                                    <th id="pendingFromHeader">Pending (From)</th>
                                    <th>Resurfaced</th>
                                    <th>New</th>
                                    <th>Resolved</th>
                                    <th id="pendingToHeader">Pending (To)</th>
                                </tr>
                            </thead>
                            <tbody id="reportTableBody"></tbody>
                            <tfoot class="fw-bold" id="reportGrandTotal"></tfoot>
                        </table>
                        <div id="moduleGroupTables"></div>
                        <div id="additionalSections"></div>
                        <div class="text-end mt-4">
                            <button class="btn btn-secondary" onclick="generatePDF()">Generate PDF</button>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </div>
	<!-- View Observations Modal -->
	<div class="modal fade" id="viewObservationsModal" tabindex="-1">
	  <div class="modal-dialog modal-xl modal-dialog-scrollable">
	    <div class="modal-content">
	      <div class="modal-header d-flex justify-content-between align-items-center">
  <div>
    <h5 class="modal-title mb-1">View Observations</h5>
    <div class="obs-legend">
      <span><i class="legend-box legend-vital"></i> Vital</span>
      <span><i class="legend-box legend-essential"></i> Essential</span>
      <span><i class="legend-box legend-desirable"></i> Desirable</span>
      <span><i class="legend-box legend-resurfaced"></i> Resurfaced</span>
      <span><i class="legend-box legend-closed"></i> Closed</span>
    </div>
  </div>
  <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
</div>
	      <div class="modal-body">
	        <!-- Date Range -->
	        <div class="row mb-3">
        	  <div class="col-md-4">
	            <label class="form-label">From Date</label>
	            <input type="date" class="form-control" id="obsFromDate">
	          </div>
        	  <div class="col-md-4">
	            <label class="form-label">To Date</label>
        	    <input type="date" class="form-control" id="obsToDate">
	          </div>
        	  <div class="col-md-4 d-flex align-items-end">
	            <button class="btn btn-primary w-100" onclick="loadObservations()">
	              Fetch Observations
	            </button>
	          </div>
	        </div>
	        <!-- Results Table -->
	        <div class="table-responsive d-none" id="observationsTableContainer">
	          <table class="table table-bordered table-hover align-middle">
	            <thead class="table-dark">
	              <tr>
	                <th>Ser</th>
        	        <th>UID</th>
	                <th>Observation</th>
	                <th class="sortable" data-key="module">Module</th>
	                <th class="sortable" data-key="group">Group</th>
	                <th class="sortable" data-key="criticality">Criticality</th>
	              </tr>
	            </thead>
	            <tbody id="observationsTableBody">
	              <!-- Rows will be injected -->
	            </tbody>
	          </table>
	        </div>
	      </div>
	    </div>
	  </div>
	</div>
    <footer class="footer-navy py-4 mt-auto">
        <div class="container">
            <div class="row align-items-center">
		    <div class="col-md-8">
		        <h5 class="mb-2"><i class="bi bi-cpu"></i> ERP Monitoring Platform</h5>
		        <p class="mb-1 opacity-75">
		            Developed by Lt Cdr Mehta, JMMIS, ND (Mbi)<br>
		            <small>Naval Dockyard, Mumbai</small>
		        </p>
		    </div>
		    <div class="col-md-4 text-md-end">
			    <div class="text-white-50 small">
			        <div>
			            <a href="/static/docs/releaseNotes.pdf" target="_blank" class="text-warning text-decoration-none fw-semibold d-block">
			                <i class="bi bi-file-earmark-pdf"></i> Latest Release Notes&nbsp;&nbsp;&nbsp;&nbsp;
			            </a>
			        </div>
			        <div>
			            <i class="bi bi-clock"></i> <span id="currentTime"></span>
			        </div>
			    </div>
			</div>
		</div>
        </div>
    </footer>
	<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
    <script>
        function updateTime() { document.getElementById('currentTime').textContent = new Date().toLocaleString('en-IN'); }
        updateTime(); setInterval(updateTime, 60000);
        async function saveObservation() {
            const form = document.getElementById('observationForm');
            const errorAlert = document.getElementById('errorAlert');
            const successAlert = document.getElementById('successAlert');
            errorAlert.classList.add('d-none'); successAlert.classList.add('d-none');
            if (!form.checkValidity()) { form.reportValidity(); return; }
            const data = { observation: form.observation.value, module_id: form.module_id.value, criticality: form.criticality.value, secret_code: form.secret_code.value };
            if (data.secret_code !== 'CYERP') { errorAlert.textContent = 'Invalid code. Enter CYERP.'; errorAlert.classList.remove('d-none'); return; }
            try {
                const response = await fetch('/save', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(data) });
                const result = await response.json();
                if (result.success) {
                    successAlert.classList.remove('d-none'); form.reset(); updateTotalCount(); setTimeout(() => bootstrap.Modal.getInstance(document.getElementById('observationModal')).hide(), 2000);
                } else { errorAlert.textContent = 'Error: ' + result.error; errorAlert.classList.remove('d-none'); }
            } catch (error) { errorAlert.textContent = 'Server error.'; errorAlert.classList.remove('d-none'); }
        }
        async function updateTotalCount() {
            try {
                const response = await fetch('/api/observations/pending/count');
                const data = await response.json();
                if (data.success) document.getElementById('totalObservations').textContent = data.count;
            } catch (error) { console.log('Count error:', error); }
        }
        async function loadInitialCount() { await updateTotalCount(); }
        loadInitialCount();
        document.getElementById('observationModal').addEventListener('show.bs.modal', () => { document.getElementById('errorAlert').classList.add('d-none'); document.getElementById('successAlert').classList.add('d-none'); });
    </script>
    <script>
        async function generateReport() {
            const fromDate = document.getElementById('reportFromDate').value;
            const toDate = document.getElementById('reportToDate').value;
            if (!fromDate || !toDate) { alert("Select both dates"); return; }
            document.getElementById('pendingFromHeader').textContent = `Pending (${fromDate})`;
            document.getElementById('pendingToHeader').textContent = `Pending (${toDate})`;
            try {
                const detailedResponse = await fetch('/api/reports/detailed', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ from_date: fromDate, to_date: toDate }) });
                const detailedResult = await detailedResponse.json();
                if (!detailedResult.success) { alert("Report error: " + (detailedResult.error || 'Unknown')); return; }
                const vitalResponse = await fetch('/api/reports/vital-details', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ from_date: fromDate, to_date: toDate }) });
                const vitalResult = await vitalResponse.json();
                if (!vitalResult.success) { alert("Vital details error: " + (vitalResult.error || 'Unknown')); return; }
                // Overall table
                const tbody = document.getElementById('reportTableBody');
                const tfoot = document.getElementById('reportGrandTotal');
                const moduleTablesDiv = document.getElementById('moduleGroupTables');
                const additionalSections = document.getElementById('additionalSections');
                tbody.innerHTML = ''; tfoot.innerHTML = ''; moduleTablesDiv.innerHTML = ''; additionalSections.innerHTML = '';
                detailedResult.overall_data.forEach(row => {
                    tbody.innerHTML += `<tr><td>${row.group}</td><td>${row.pending_from}</td><td>${row.resurfaced}</td><td>${row.new}</td><td>${row.resolved}</td><td>${row.pending_to}</td></tr>`;
                });
                const gt = detailedResult.grand_total;
                tfoot.innerHTML = `<tr><td>GRAND TOTAL</td><td>${gt.pending_from}</td><td>${gt.resurfaced}</td><td>${gt.new_obs}</td><td>${gt.resolved}</td><td>${gt.pending_to}</td></tr>`;
                // Module group tables
                detailedResult.module_data.forEach(groupData => {
                    let groupHtml = `<div class="mt-5"><h5 class="fw-bold">${groupData.group_name} - Pending Vital Observations</h5><table class="table table-bordered mt-3"><thead class="table-light"><tr><th>MODULE</th><th>Pending (${fromDate})</th><th>Resurfaced</th><th>New</th><th>Resolved</th><th>Pending (${toDate})</th></tr></thead><tbody>`;
                    groupData.modules.forEach(module => {
                        groupHtml += `<tr><td>${module.module_name}</td><td>${module.pending_from}</td><td>${module.resurfaced}</td><td>${module.new}</td><td>${module.resolved}</td><td>${module.pending_to}</td></tr>`;
                    });
                    groupHtml += `</tbody></table><h6 class="fw-bold mt-3">AREAS OF CONCERN:</h6><ul class="list-group list-group-flush">`;
                    groupData.vital_observations.forEach(obs => {
                        const date = new Date(obs.timestamp).toLocaleDateString('en-IN');
                        groupHtml += `<li class="list-group-item"><strong>${obs.module_name}:</strong> ${obs.observation}<br><small class="text-muted">Date: ${date} | Status: ${obs.status}</small></li>`;
                    });
                    if (groupData.vital_observations.length === 0) groupHtml += '<li class="list-group-item text-muted">No Vital observations found.</li>';
                    groupHtml += '</ul></div>';
                    moduleTablesDiv.innerHTML += groupHtml;
                });
                // New sections
                additionalSections.innerHTML = `
                    <div class="mt-5">
                        <h5 class="fw-bold">MODULES UNDER DEVELOPMENT</h5>
                        <ul class="list-group list-group-flush">
                            <li class="list-group-item">Coster</li>
                            <li class="list-group-item">E-Samagri</li>
                            <li class="list-group-item">MHMS</li>
                            <li class="list-group-item">YAMS</li>
                        </ul>
                    </div>
                    <div class="mt-5">
                        <h5 class="fw-bold">DETAILS OF VITAL OBSERVATIONS IDENTIFIED IN THIS PERIOD</h5>
                        <table class="table table-bordered mt-3">
                            <thead class="table-light">
                                <tr><th>IDENTIFIED</th><th>RESOLVED</th></tr>
                            </thead>
                            <tbody>
                                <tr>
                                    <td><ul class="list-group list-group-flush mb-0">`;
                vitalResult.identified.forEach(obs => {
                    const date = new Date(obs.date).toLocaleDateString('en-IN');
                    additionalSections.innerHTML += `<li class="list-group-item"><strong>${obs.module_name}:</strong> ${obs.observation} <small class="text-muted">(Date: ${date}, Status: ${obs.status})</small></li>`;
                });
                if (vitalResult.identified.length === 0) additionalSections.innerHTML += '<li class="list-group-item">None identified</li>';
                additionalSections.innerHTML += `</ul></td><td><ul class="list-group list-group-flush mb-0">`;
                vitalResult.resolved.forEach(obs => {
                    const date = new Date(obs.date).toLocaleDateString('en-IN');
                    additionalSections.innerHTML += `<li class="list-group-item"><strong>${obs.module_name}:</strong> ${obs.observation} <small class="text-muted">(Date: ${date})</small></li>`;
                });
                if (vitalResult.resolved.length === 0) additionalSections.innerHTML += '<li class="list-group-item">None resolved</li>';
                additionalSections.innerHTML += '</ul></td></tr></tbody></table></div>';
                document.getElementById('reportResult').classList.remove('d-none');
            } catch (error) { alert('Generation failed: ' + error); }
        }
    </script>
	<script>
async function loadObservations() {
  const fromDate = document.getElementById('obsFromDate').value;
  const toDate = document.getElementById('obsToDate').value;

  if (!fromDate || !toDate) {
    alert('Please select both From and To dates');
    return;
  }

  const response = await fetch('/api/observations/range', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      from_date: fromDate,
      to_date: toDate
    })
  });

  const result = await response.json();

  if (!result.success) {
    alert('Failed to fetch observations');
    return;
  }

  const tbody = document.getElementById('observationsTableBody');
  const container = document.getElementById('observationsTableContainer');

  tbody.innerHTML = '';

  const groupColorMap = {};
let colorIndex = 0;

result.data.forEach((row, index) => {
  let rowClass = '';

  if (row.status === 'CLOSED') {
    rowClass = 'obs-closed';
  } else if (row.status === 'RESURFACED') {
    rowClass = 'obs-resurfaced';
  } else if (row.criticality === 'Vital') {
    rowClass = 'obs-vital';
  } else if (row.criticality === 'Essential') {
    rowClass = 'obs-essential';
  } else if (row.criticality === 'Desirable') {
    rowClass = 'obs-desirable';
  }

  tbody.innerHTML += `
    <tr class="${rowClass}">
      <td>${index + 1}</td>
      <td>${row.id}</td>
      <td>${row.observation}</td>
      <td>${row.module_name}</td>
      <td>${row.group_name}</td>
      <td>${row.criticality}</td>
    </tr>
  `;
});

  container.classList.remove('d-none');
}
</script>
<script>
let currentSortKey = null;
let currentSortAsc = true;

document.addEventListener('click', function (e) {
  if (!e.target.classList.contains('sortable')) return;

  const key = e.target.dataset.key;
  const tbody = document.getElementById('observationsTableBody');
  const rows = Array.from(tbody.querySelectorAll('tr'));

  // Toggle sort direction
  if (currentSortKey === key) {
    currentSortAsc = !currentSortAsc;
  } else {
    currentSortKey = key;
    currentSortAsc = true;
  }

  rows.sort((a, b) => {
    let valA, valB;

    if (key === 'module') {
      valA = a.cells[3].innerText;
      valB = b.cells[3].innerText;
    } else if (key === 'group') {
      valA = a.cells[4].innerText;
      valB = b.cells[4].innerText;
    } else if (key === 'criticality') {
      valA = a.cells[5].innerText;
      valB = b.cells[5].innerText;
    }

    if (valA < valB) return currentSortAsc ? -1 : 1;
    if (valA > valB) return currentSortAsc ? 1 : -1;
    return 0;
  });

  // Re-render rows and re-number Ser
  tbody.innerHTML = '';
  rows.forEach((row, index) => {
    row.cells[0].innerText = index + 1;
    tbody.appendChild(row);
  });
});
</script>

<script>
async function loadCharts() {

  // Chart 1 - Criticality Trend
  const critRes = await fetch('/api/charts/criticality-trend');
  const critData = await critRes.json();

  new Chart(document.getElementById('criticalityTrendChart'), {
    type: 'line',
    data: {
      labels: critData.labels,
      datasets: [
        { label: 'Vital', data: critData.vital, borderColor: '#e51f1f' },
        { label: 'Essential', data: critData.essential, borderColor: '#f2a134' },
        { label: 'Desirable', data: critData.desirable, borderColor: '#f7e379' }
      ]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false
    }
  });

  // Chart 2 - Vital by Module
  const modRes = await fetch('/api/charts/vital-module-trend');
  const modData = await modRes.json();

  new Chart(document.getElementById('moduleVitalTrendChart'), {
    type: 'line',
    data: {
      labels: modData.labels,
      datasets: modData.datasets
    },
    options: {
      responsive: true,
      maintainAspectRatio: false
    }
  });
}

document.addEventListener('DOMContentLoaded', loadCharts);
</script>

    <script>
        function generatePDF() {
            const fromDate = document.getElementById('reportFromDate').value;
            const toDate = document.getElementById('reportToDate').value;
            if (!fromDate || !toDate) { alert("Select both dates"); return; }
            fetch('/api/reports/pdf', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ from_date: fromDate, to_date: toDate }) })
                .then(response => response.blob())
                .then(blob => {
                    const url = window.URL.createObjectURL(blob);
                    const win = window.open(url);
                    win.onload = () => win.print();
                })
                .catch(error => alert('PDF failed: ' + error));
        }
        // Lifecycle JS (modals)
        async function loadModuleGroups() {
            try {
                const response = await fetch('/api/module-groups');
                const data = await response.json();
                if (data.success) {
                    window.moduleGroups = data.data;
                    populateGroupDropdowns();
                    setupGroupChangeListeners();
                }
            } catch (error) { console.error('Groups load error:', error); }
        }
        function populateGroupDropdowns() {
            const groups = window.moduleGroups || [];
            const resurfaceGroup = document.getElementById('resurfaceGroup');
            resurfaceGroup.innerHTML = '<option value="">Select Group</option>';
            const closeGroup = document.getElementById('closeGroup');
            closeGroup.innerHTML = '<option value="">Select Group</option>';
            groups.forEach(group => {
                const option = document.createElement('option');
                option.value = group.group_id;
                option.textContent = group.group_name;
                resurfaceGroup.appendChild(option.cloneNode(true));
                closeGroup.appendChild(option.cloneNode(true));
            });
        }
        function setupGroupChangeListeners() {
            document.getElementById('resurfaceGroup').addEventListener('change', function() {
                const groupId = this.value;
                const moduleSelect = document.getElementById('resurfaceModule');
                moduleSelect.innerHTML = '<option value="">Select Module</option>';
                if (!groupId) return;
                const group = window.moduleGroups.find(g => g.group_id == groupId);
                if (group && group.modules) group.modules.forEach(module => {
                    const option = document.createElement('option');
                    option.value = module.module_id;
                    option.textContent = module.module_name;
                    moduleSelect.appendChild(option);
                });
            });
            document.getElementById('closeGroup').addEventListener('change', function() {
                const groupId = this.value;
                const moduleSelect = document.getElementById('closeModule');
                moduleSelect.innerHTML = '<option value="">Select Module</option>';
                if (!groupId) return;
                const group = window.moduleGroups.find(g => g.group_id == groupId);
                if (group && group.modules) group.modules.forEach(module => {
                    const option = document.createElement('option');
                    option.value = module.module_id;
                    option.textContent = module.module_name;
                    moduleSelect.appendChild(option);
                });
            });
            document.getElementById('resurfaceModule').addEventListener('change', async function() {
                const moduleId = this.value;
                const listDiv = document.getElementById('resurfaceList');
                if (!moduleId) { listDiv.innerHTML = ''; return; }
                try {
                    const response = await fetch('/api/observations/closed', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ module_id: moduleId }) });
                    const result = await response.json();
                    if (result.success) {
                        const observations = result.data;
                        if (observations.length === 0) listDiv.innerHTML = '<p class="text-muted text-center">No CLOSED observations.</p>';
                        else {
                            let html = '<div class="list-group">';
                            observations.forEach(obs => {
                                const date = new Date(obs.timestamp).toLocaleDateString('en-IN');
                                html += `<div class="list-group-item"><input class="form-check-input me-2" type="checkbox" value="${obs.id}" id="resurface_${obs.id}"><label class="form-check-label w-100" for="resurface_${obs.id}"><div class="d-flex justify-content-between"><span>${obs.observation}</span><span class="badge bg-secondary">${date}</span></div><small class="text-muted d-block">Criticality: ${obs.criticality}</small></label></div>`;
                            });
                            html += '</div>';
                            listDiv.innerHTML = html;
                        }
                    } else listDiv.innerHTML = '<p class="text-danger">Load failed.</p>';
                } catch (error) { console.error('Load error:', error); listDiv.innerHTML = '<p class="text-danger">Error loading.</p>'; }
            });
            document.getElementById('closeModule').addEventListener('change', async function() {
                const moduleId = this.value;
                const listDiv = document.getElementById('closeList');
                if (!moduleId) { listDiv.innerHTML = ''; return; }
                try {
                    const response = await fetch('/api/observations/open-resurfaced', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ module_id: moduleId }) });
                    const result = await response.json();
                    if (result.success) {
                        const observations = result.data;
                        if (observations.length === 0) listDiv.innerHTML = '<p class="text-muted text-center">No OPEN or RESURFACED observations.</p>';
                        else {
                            let html = '<div class="list-group">';
                            observations.forEach(obs => {
                                const date = new Date(obs.timestamp).toLocaleDateString('en-IN');
                                const statusClass = obs.status === 'OPEN' ? 'bg-primary' : 'bg-warning';
                                html += `<div class="list-group-item"><input class="form-check-input me-2" type="checkbox" value="${obs.id}" id="close_${obs.id}"><label class="form-check-label w-100" for="close_${obs.id}"><div class="d-flex justify-content-between"><span>${obs.observation}</span><div><span class="badge ${statusClass} me-2">${obs.status}</span><span class="badge bg-secondary">${date}</span></div></div><small class="text-muted d-block">Criticality: ${obs.criticality}</small></label></div>`;
                            });
                            html += '</div>';
                            listDiv.innerHTML = html;
                        }
                    } else listDiv.innerHTML = '<p class="text-danger">Load failed.</p>';
                } catch (error) { console.error('Load error:', error); listDiv.innerHTML = '<p class="text-danger">Error loading.</p>'; }
            });
        }
        async function submitResurface() {
            const checkboxes = document.querySelectorAll('#resurfaceList input[type="checkbox"]:checked');
            const ids = Array.from(checkboxes).map(cb => cb.value);
            if (ids.length === 0) { alert('Select at least one.'); return; }
            try {
                const response = await fetch('/api/observations/resurface', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ ids }) });
                const result = await response.json();
                if (result.success) { alert('Resurfaced!'); document.getElementById('resurfaceModule').dispatchEvent(new Event('change')); updateTotalCount(); } else alert('Failed: ' + (result.error || 'Unknown'));
            } catch (error) { console.error('Error:', error); alert('Error.'); }
        }
        async function submitClose() {
            const checkboxes = document.querySelectorAll('#closeList input[type="checkbox"]:checked');
            const ids = Array.from(checkboxes).map(cb => cb.value);
            if (ids.length === 0) { alert('Select at least one.'); return; }
            try {
                const response = await fetch('/api/observations/close', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ ids }) });
                const result = await response.json();
                if (result.success) { alert('Closed!'); document.getElementById('closeModule').dispatchEvent(new Event('change')); updateTotalCount(); } else alert('Failed: ' + (result.error || 'Unknown'));
            } catch (error) { console.error('Error:', error); alert('Error.'); }
        }
        document.addEventListener('DOMContentLoaded', function() {
            loadModuleGroups();
            document.getElementById('resurfaceModal').addEventListener('show.bs.modal', () => {
                document.getElementById('resurfaceGroup').value = ''; document.getElementById('resurfaceModule').innerHTML = '<option value="">Select Module</option>'; document.getElementById('resurfaceList').innerHTML = '';
            });
            document.getElementById('closeModal').addEventListener('show.bs.modal', () => {
                document.getElementById('closeGroup').value = ''; document.getElementById('closeModule').innerHTML = '<option value="">Select Module</option>'; document.getElementById('closeList').innerHTML = '';
            });
        });
    </script>
<script>
async function loadCharts() {

  // Chart 1 - Criticality Trend
  const critRes = await fetch('/api/charts/criticality-trend');
  const critData = await critRes.json();

  new Chart(document.getElementById('criticalityTrendChart'), {
    type: 'line',
    data: {
      labels: critData.labels,
      datasets: [
        { label: 'Vital', data: critData.vital, borderColor: '#e51f1f' },
        { label: 'Essential', data: critData.essential, borderColor: '#f2a134' },
        { label: 'Desirable', data: critData.desirable, borderColor: '#f7e379' }
      ]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false
    }
  });

  // Chart 2 - Vital by Module
  const modRes = await fetch('/api/charts/vital-module-trend');
  const modData = await modRes.json();

  new Chart(document.getElementById('moduleVitalTrendChart'), {
    type: 'line',
    data: {
      labels: modData.labels,
      datasets: modData.datasets
    },
    options: {
      responsive: true,
      maintainAspectRatio: false
    }
  });
}

document.addEventListener('DOMContentLoaded', loadCharts);
</script>

</body>
</html>
    '''

# ========== API ENDPOINTS ==========
@app.route('/save', methods=['POST'])
def save_observation():
    try:
        data = request.json
        if data.get('secret_code') != SECRET_CODE:
            return jsonify({'success': False, 'error': 'Invalid code'}), 403
        required = ['observation', 'module_id', 'criticality']
        for f in required:
            if not data.get(f):
                return jsonify({'success': False, 'error': f'Missing {f}'}), 400
        conn = get_db_connection()
        conn.execute("INSERT INTO observations (observation, module_id, criticality, status) VALUES (?, ?, ?, 'OPEN')", (data['observation'], data['module_id'], data['criticality']))
        conn.commit()
        conn.close()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': 'Server error'}), 500

@app.route('/api/observations/pending/count')
def pending_count():
    try:
        conn = get_db_connection()
        count = conn.execute("SELECT COUNT(*) FROM observations WHERE status IN ('OPEN', 'RESURFACED')").fetchone()[0]
        conn.close()
        return jsonify({'success': True, 'count': count})
    except:
        return jsonify({'success': False, 'count': 0})

@app.route('/api/observations/close', methods=['POST'])
def close_observations():
    ids = request.json.get('ids', [])
    if not ids: return jsonify({'success': False}), 400
    conn = get_db_connection()
    conn.execute(f"UPDATE observations SET status='CLOSED', closed_on=CURRENT_TIMESTAMP WHERE id IN ({','.join('?'*len(ids))})", ids)
    conn.commit()
    conn.close()
    return jsonify({'success': True})

@app.route('/api/observations/resurface', methods=['POST'])
def resurface_observations():
    ids = request.json.get('ids', [])
    if not ids: return jsonify({'success': False}), 400
    conn = get_db_connection()
    conn.execute(f"UPDATE observations SET status='RESURFACED', resurfaced_on=CURRENT_TIMESTAMP WHERE id IN ({','.join('?'*len(ids))})", ids)
    conn.commit()
    conn.close()
    return jsonify({'success': True})

@app.route('/api/reports/detailed', methods=['POST'])
def detailed_report():
    data = request.json
    from_date = data.get('from_date')
    to_date = data.get('to_date')
    if not from_date or not to_date: return jsonify({'success': False, 'error': 'Dates required'}), 400
    from_ts = f"{from_date} 00:00:00"
    to_ts = f"{to_date} 23:59:59"
    conn = get_db_connection()
    cur = conn.cursor()
    overall_data = []
    grand = {'pending_from': 0, 'resurfaced': 0, 'new_obs': 0, 'resolved': 0, 'pending_to': 0}
    groups = cur.execute("SELECT group_id, group_name FROM module_groups ORDER BY group_name").fetchall()
    for g in groups:
        row = cur.execute("""
            SELECT 
                SUM(CASE WHEN o.timestamp <= ? AND (o.status = 'OPEN' OR (o.status = 'RESURFACED' AND o.resurfaced_on <= ?)) AND o.criticality = 'Vital' THEN 1 ELSE 0 END) AS pending_from,
                SUM(CASE WHEN o.status = 'RESURFACED' AND o.resurfaced_on BETWEEN ? AND ? AND o.criticality = 'Vital' THEN 1 ELSE 0 END) AS resurfaced,
                SUM(CASE WHEN o.timestamp BETWEEN ? AND ? AND o.criticality = 'Vital' THEN 1 ELSE 0 END) AS new,
                SUM(CASE WHEN o.status = 'CLOSED' AND o.closed_on BETWEEN ? AND ? AND o.criticality = 'Vital' THEN 1 ELSE 0 END) AS resolved
            FROM observations o JOIN modules m ON o.module_id = m.module_id WHERE m.group_id = ? AND o.criticality = 'Vital'
        """, (from_ts, from_ts, from_ts, to_ts, from_ts, to_ts, from_ts, to_ts, g['group_id'])).fetchone()
        p_from = row['pending_from'] or 0
        res = row['resurfaced'] or 0
        new = row['new'] or 0
        reslv = row['resolved'] or 0
        p_to = p_from + res + new - reslv
        overall_data.append({'group': g['group_name'], 'pending_from': p_from, 'resurfaced': res, 'new': new, 'resolved': reslv, 'pending_to': p_to})
        grand['pending_from'] += p_from; grand['resurfaced'] += res; grand['new_obs'] += new; grand['resolved'] += reslv; grand['pending_to'] += p_to
    module_data = []
    for g in groups:
        mods = cur.execute("SELECT module_id, module_name FROM modules WHERE group_id = ? ORDER BY module_name", (g['group_id'],)).fetchall()
        mod_stats = []
        for m in mods:
            row = cur.execute("""
                SELECT 
                    SUM(CASE WHEN o.timestamp <= ? AND (o.status = 'OPEN' OR (o.status = 'RESURFACED' AND o.resurfaced_on <= ?)) AND o.criticality = 'Vital' THEN 1 ELSE 0 END) AS pending_from,
                    SUM(CASE WHEN o.status = 'RESURFACED' AND o.resurfaced_on BETWEEN ? AND ? AND o.criticality = 'Vital' THEN 1 ELSE 0 END) AS resurfaced,
                    SUM(CASE WHEN o.timestamp BETWEEN ? AND ? AND o.criticality = 'Vital' THEN 1 ELSE 0 END) AS new,
                    SUM(CASE WHEN o.status = 'CLOSED' AND o.closed_on BETWEEN ? AND ? AND o.criticality = 'Vital' THEN 1 ELSE 0 END) AS resolved
                FROM observations o WHERE o.module_id = ? AND o.criticality = 'Vital'
            """, (from_ts, from_ts, from_ts, to_ts, from_ts, to_ts, from_ts, to_ts, m['module_id'])).fetchone()
            p_from = row['pending_from'] or 0
            res = row['resurfaced'] or 0
            new = row['new'] or 0
            reslv = row['resolved'] or 0
            p_to = p_from + res + new - reslv
            mod_stats.append({'module_name': m['module_name'], 'pending_from': p_from, 'resurfaced': res, 'new': new, 'resolved': reslv, 'pending_to': p_to})
        vital_obs = cur.execute("""
            SELECT o.observation, o.status, o.timestamp, m.module_name FROM observations o JOIN modules m ON o.module_id = m.module_id 
            WHERE m.group_id = ? AND o.criticality = 'Vital' AND o.status IN ('OPEN', 'RESURFACED') ORDER BY o.timestamp DESC
        """, (g['group_id'],)).fetchall()
        module_data.append({'group_name': g['group_name'], 'modules': mod_stats, 'vital_observations': [dict(o) for o in vital_obs]})
    conn.close()
    return jsonify({'success': True, 'overall_data': overall_data, 'grand_total': grand, 'module_data': module_data})

@app.route('/api/reports/vital-details', methods=['POST'])
def vital_details():
    data = request.json
    from_date = data.get('from_date')
    to_date = data.get('to_date')
    if not from_date or not to_date: return jsonify({'success': False, 'error': 'Dates required'}), 400
    from_ts = f"{from_date} 00:00:00"
    to_ts = f"{to_date} 23:59:59"
    conn = get_db_connection()
    cur = conn.cursor()
    # Identified: New or Resurfaced Vitals in period, OPEN/RESURFACED
    identified = cur.execute("""
        SELECT m.module_name, o.observation, o.status, o.timestamp as date FROM observations o JOIN modules m ON o.module_id = m.module_id 
        WHERE o.criticality = 'Vital' AND o.status IN ('OPEN', 'RESURFACED') AND 
        (o.timestamp BETWEEN ? AND ? OR (o.status = 'RESURFACED' AND o.resurfaced_on BETWEEN ? AND ?)) ORDER BY o.timestamp DESC LIMIT 20
    """, (from_ts, to_ts, from_ts, to_ts)).fetchall()
    # Resolved: Vitals closed in period
    resolved = cur.execute("""
        SELECT m.module_name, o.observation, o.closed_on as date FROM observations o JOIN modules m ON o.module_id = m.module_id 
        WHERE o.criticality = 'Vital' AND o.status = 'CLOSED' AND o.closed_on BETWEEN ? AND ? ORDER BY o.closed_on DESC LIMIT 20
    """, (from_ts, to_ts)).fetchall()
    conn.close()
    return jsonify({'success': True, 'identified': [dict(i) for i in identified], 'resolved': [dict(r) for r in resolved]})

@app.route('/api/reports/pdf', methods=['POST'])
def generate_report_pdf():
    data = request.get_json()
    from_date = data['from_date']
    to_date = data['to_date']
    from_ts = f"{from_date} 00:00:00"
    to_ts = f"{to_date} 23:59:59"
    # Get detailed data
    with app.test_request_context(json=data):
        detailed_resp = detailed_report().get_json()
    with app.test_request_context(json=data):
        vital_resp = vital_details().get_json()
    overall_data = detailed_resp['overall_data']
    grand_total = detailed_resp['grand_total']
    module_data = detailed_resp['module_data']
    identified = vital_resp['identified']
    resolved = vital_resp['resolved']
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, leftMargin=36, rightMargin=36, topMargin=50, bottomMargin=36)
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle('CustomTitle', parent=styles['Title'], fontSize=16, spaceAfter=20, alignment=TA_CENTER)
    subtitle_style = ParagraphStyle('CustomSubtitle', parent=styles['Heading2'], fontSize=12, spaceAfter=12, alignment=TA_CENTER)
    bold_style = ParagraphStyle('CustomBold', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=11, spaceAfter=8)
    normal_style = ParagraphStyle('CustomNormal', parent=styles['Normal'], fontSize=9, alignment=TA_LEFT, leading=10)
    elements = []
    elements.append(Paragraph("NAVYOJANA PROJECT BRIEF", title_style))
    elements.append(Paragraph(f"(From {from_date} to {to_date})", subtitle_style))
    elements.append(Spacer(1, 12))
    elements.append(Paragraph("OVERALL PENDING VITAL OBSERVATIONS", bold_style))
    elements.append(Spacer(1, 6))
    # Overall table with widths
    table_data = [["GROUP", f"Pending as on {from_date}", "Resurfaced", "New", "Resolved", f"Pending as on {to_date}"]]
    for r in overall_data:
        table_data.append([Paragraph(r['group'], normal_style), str(r['pending_from']), str(r['resurfaced']), str(r['new']), str(r['resolved']), str(r['pending_to'])])
    table_data.append([Paragraph("GRAND TOTAL", bold_style), str(grand_total['pending_from']), str(grand_total['resurfaced']), str(grand_total['new_obs']), str(grand_total['resolved']), str(grand_total['pending_to'])])
    table = Table(table_data, colWidths=[120, 70, 60, 50, 50, 70], repeatRows=1)
    table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.lightgrey),
        ('GRID', (0,0), (-1,-1), 1, colors.black),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0), (-1,-1), 10),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('ROWBACKGROUNDS', (0,1), (-1,-2), [colors.white, colors.lightgrey])
    ]))
    elements.append(table)
    elements.append(Spacer(1, 18))
    # Module tables
    for grp in module_data:
        elements.append(Paragraph(f"{grp['group_name']} - Pending Vital Observations", subtitle_style))
        elements.append(Spacer(1, 6))
        mod_table_data = [["MODULE", f"Pending as on {from_date}", "Resurfaced", "New", "Resolved", f"Pending as on {to_date}"]]
        for m in grp['modules']:
            p = Paragraph(m['module_name'], ParagraphStyle('ModName', parent=normal_style, fontSize=8, alignment=TA_LEFT))
            mod_table_data.append([p, str(m['pending_from']), str(m['resurfaced']), str(m['new']), str(m['resolved']), str(m['pending_to'])])
        mod_table = Table(mod_table_data, colWidths=[200, 60, 50, 50, 50, 60], repeatRows=1)
        mod_table.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.lightgrey),
            ('GRID', (0,0), (-1,-1), 1, colors.black),
            ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
            ('FONTSIZE', (0,0), (-1,-1), 8),
            ('ALIGN', (1,0), (-1,-1), 'CENTER'),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, colors.lightgrey])
        ]))
        elements.append(mod_table)
        elements.append(Spacer(1, 12))
        elements.append(Paragraph("AREAS OF CONCERN:", bold_style))
        elements.append(Spacer(1, 6))
        if grp['vital_observations']:
            for obs in grp['vital_observations']:
                obs_para = Paragraph(f"<b>{obs['module_name']}:</b> {obs['observation']} (Date: {obs['timestamp'][:10]}, Status: {obs['status']})", normal_style)
                elements.append(obs_para)
                elements.append(Spacer(1, 4))
        else:
            elements.append(Paragraph("No Vital observations found.", normal_style))
        elements.append(Spacer(1, 18))
    # Modules under development
    elements.append(Paragraph("MODULES UNDER DEVELOPMENT", subtitle_style))
    elements.append(Spacer(1, 6))
    dev_list = Table([["- Coster", ""], ["- E-Samagri", ""], ["- MHMS", ""], ["- YAMS", ""]], colWidths=[250, 273])
    dev_list.setStyle(TableStyle([('FONTSIZE', (0,0), (-1,-1), 10), ('ALIGN', (0,0), (-1,-1), 'LEFT')]))
    elements.append(dev_list)
    elements.append(Spacer(1, 18))
    # Vital details table
    elements.append(Paragraph("DETAILS OF VITAL OBSERVATIONS IDENTIFIED IN THIS PERIOD", subtitle_style))
    elements.append(Spacer(1, 6))
    identified_list = []
    for obs in identified:
        identified_list.append(Paragraph(f"<b>{obs['module_name']}:</b> {obs['observation']} (Date: {obs['date'][:10]}, Status: {obs['status']})", normal_style))
    resolved_list = []
    for obs in resolved:
        resolved_list.append(Paragraph(f"<b>{obs['module_name']}:</b> {obs['observation']} (Date: {obs['date'][:10]})", normal_style))
    vital_table_data = [["IDENTIFIED", "RESOLVED"]]
    vital_table_data.append([identified_list if identified_list else Paragraph("None identified", normal_style), resolved_list if resolved_list else Paragraph("None resolved", normal_style)])
    vital_table = Table(vital_table_data, colWidths=[250, 273])
    vital_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.lightgrey),
        ('GRID', (0,0), (-1,-1), 1, colors.black),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0), (-1,-1), 9),
        ('ALIGN', (0,0), (0,0), 'CENTER'),
        ('VALIGN', (0,0), (-1,-1), 'TOP')
    ]))
    elements.append(vital_table)
    doc.build(elements)
    buffer.seek(0)
    return send_file(buffer, as_attachment=False, mimetype='application/pdf', download_name='Navyojana_Project_Brief.pdf')

@app.route('/api/module-groups', methods=['GET'])
def get_module_groups():
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT * FROM module_groups ORDER BY group_name")
        groups = cur.fetchall()
        result = []
        for group in groups:
            cur.execute("SELECT module_id, module_name FROM modules WHERE group_id = ? ORDER BY module_name", (group['group_id'],))
            modules = cur.fetchall()
            result.append({'group_id': group['group_id'], 'group_name': group['group_name'], 'modules': [{'module_id': m['module_id'], 'module_name': m['module_name']} for m in modules]})
        conn.close()
        return jsonify({'success': True, 'data': result})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/observations/closed', methods=['POST'])
def get_closed_observations():
    try:
        module_id = request.json.get('module_id')
        if not module_id: return jsonify({'success': False, 'error': 'Module ID required'}), 400
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT o.id, o.observation, o.criticality, o.timestamp FROM observations o WHERE o.module_id = ? AND o.status = 'CLOSED' ORDER BY o.timestamp DESC", (module_id,))
        observations = cur.fetchall()
        conn.close()
        return jsonify({'success': True, 'data': [dict(obs) for obs in observations]})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/observations/open-resurfaced', methods=['POST'])
def get_open_resurfaced_observations():
    try:
        module_id = request.json.get('module_id')
        if not module_id: return jsonify({'success': False, 'error': 'Module ID required'}), 400
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT o.id, o.observation, o.criticality, o.status, o.timestamp FROM observations o WHERE o.module_id = ? AND o.status IN ('OPEN', 'RESURFACED') ORDER BY o.timestamp DESC", (module_id,))
        observations = cur.fetchall()
        conn.close()
        return jsonify({'success': True, 'data': [dict(obs) for obs in observations]})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/observations/range', methods=['POST'])
def observations_by_date_range():
    data = request.get_json(force=True)

    from_date = data.get('from_date')
    to_date = data.get('to_date')

    if not from_date or not to_date:
        return jsonify({'success': False, 'error': 'Invalid date range'}), 400

    conn = get_db_connection()
    conn.row_factory = sqlite3.Row

    query = """
    WITH pending_counts AS (
        SELECT
            g.group_id,
            g.group_name,
            m.module_id,
            m.module_name,
            COUNT(o.id) AS pending_count
        FROM observations o
        JOIN modules m ON o.module_id = m.module_id
        JOIN module_groups g ON m.group_id = g.group_id
        WHERE o.status IN ('OPEN', 'RESURFACED')
        GROUP BY g.group_id, m.module_id
    )
    SELECT
        o.id               AS id,
        o.observation      AS observation,
        g.group_name       AS group_name,
        m.module_name      AS module_name,
        o.criticality      AS criticality,
        o.status           AS status,
        o.timestamp        AS timestamp,
        IFNULL(pc.pending_count, 0) AS module_pending
    FROM observations o
    JOIN modules m ON o.module_id = m.module_id
    JOIN module_groups g ON m.group_id = g.group_id
    LEFT JOIN pending_counts pc
           ON pc.module_id = m.module_id
    WHERE date(o.timestamp) BETWEEN ? AND ?
    ORDER BY
        (
          SELECT SUM(pending_count)
          FROM pending_counts
          WHERE group_id = g.group_id
        ) DESC,
        module_pending DESC,
        o.timestamp DESC;
    """

    rows = conn.execute(query, (from_date, to_date)).fetchall()
    conn.close()

    return jsonify({
        'success': True,
        'data': [dict(row) for row in rows]
    })

@app.route('/api/charts/criticality-trend')
def criticality_trend():
    conn = get_db_connection()

    query = """
    SELECT
  date(timestamp) AS obs_date,
  criticality,
  COUNT(*) AS count
FROM observations
WHERE date(timestamp) >= date('now', '-6 days')
GROUP BY obs_date, criticality
ORDER BY obs_date;
    """

    rows = conn.execute(query).fetchall()
    conn.close()

    data = {}
    for r in rows:
        date = r['obs_date']
        crit = r['criticality']
        data.setdefault(date, {'Vital': 0, 'Essential': 0, 'Desirable': 0})
        data[date][crit] = r['count']

    return jsonify({
        'labels': list(data.keys()),
        'vital': [v['Vital'] for v in data.values()],
        'essential': [v['Essential'] for v in data.values()],
        'desirable': [v['Desirable'] for v in data.values()]
    })



@app.route('/api/charts/vital-module-trend')
def vital_module_trend():
    conn = get_db_connection()

    query = """
SELECT
  date(o.timestamp) AS obs_date,
  m.module_name,
  COUNT(*) AS count
FROM observations o
JOIN modules m ON o.module_id = m.module_id
WHERE o.criticality = 'Vital'
  AND date(o.timestamp) >= date('now', '-6 days')
GROUP BY obs_date, m.module_name
ORDER BY obs_date;
    """

    rows = conn.execute(query).fetchall()
    conn.close()

    labels = sorted({r['obs_date'] for r in rows})
    modules = {}

    for r in rows:
        modules.setdefault(r['module_name'], {d: 0 for d in labels})
        modules[r['module_name']][r['obs_date']] = r['count']

    datasets = [
        {
            'label': module,
            'data': list(counts.values())
        }
        for module, counts in modules.items()
    ]

    return jsonify({
        'labels': labels,
        'datasets': datasets
    })



if __name__ == '__main__':
    init_database()
    print(f"Starting ERP Monitoring Platform on port {PORT}")
    print(f"Access at: http://140.245.12.117:{PORT}")
    app.run(host='0.0.0.0', port=PORT, debug=DEBUG)