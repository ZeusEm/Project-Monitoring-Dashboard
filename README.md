# NAVYOJANA — ERP Monitoring Platform 🚀⚓

**Flask-based monitoring & reporting for ERP observations** — designed for naval operations, audit-friendly, and built to be demonstrable to senior leadership.  
_Tracks observations, supports lifecycle actions (Open → Resurfaced → Closed), generates management-grade PDF briefs, and visualizes trends._

- A lightweight, on-prem ERP observation monitoring system tailored for secure naval deployments.  
- Quick deployment, auditable workflows, summary PDF briefs for leadership, and visual trend insights — all on an Oracle Free Tier VM.  
- Clone, install, run; demo-ready within minutes. See **Quickstart** below.

---

## 🔥 Highlights
- ✅ **Lifecycle-aware observations**: Open / Resurfaced / Closed states with timestamps.  
- 📊 **Dashboard charts**: criticality trend & module-wise vital trends (week-wise).  
- 🧾 **Management PDF**: Print-ready, Arial, heading/text sizing rules, auto-open print dialog.  
- 🧭 **Ordered reporting**: Groups/modules ordered by pending counts (OPEN + RESURFACED) — management-first.  
- 🖥️ **Simple deployment**: Flask + SQLite, `systemd` auto-start, runs on Oracle Free Tier.  
- 🛡️ **ISO-aware design**: Minimal attack surface, env-based secrets, DB persistency & backups recommended.  
- 🧰 **Admin workflows**: Mark observations Resurfaced / Close in bulk; exportable and traceable.

---

## 📦 Features & Functionality
- Modular design: `module_groups` → `modules` → `observations`.  
- Idempotent DB seeding & robust schema (status, closed_on, resurfaced_on).  
- One-click PDF briefs generated server-side (ReportLab) and opened in the print dialog.  
- Read-only and admin APIs for aggregation and lifecycle operations.  
- Responsive UI: compact charts, sortable and color-coded observation lists.  
- CLI-friendly: `sqlite3` verification and safe admin operations.  
- Lightweight: no external DB/service required for demo — runs on SQLite.

---

## 🚀 Quickstart (dev/demo)

#### 1. Clone
#### 2. Create virtualenv
1. python3 -m venv venv
2. source venv/bin/activate
#### 3. Install packages/ dependencies
#### 4. Run
- python app.py
#### 5. Open http://127.0.0.1:5000 or http://<VM_PUBLIC_IP>:5000

---

## 🧭 Recommended Production Steps (Oracle VM)
- Create a system virtualenv and run app under a dedicated user ubuntu.
- Use systemd service (ExecStart → venv/bin/python app.py) to auto-start on reboot.
- Open OCI security list for port 5000 (or proxy via Nginx on 80/443).
- Move SECRET_CODE and any secrets to environment variables and never commit them.

---

## 📊 Charts & Reports
- **Chart endpoints**: `/api/charts/criticality-trend` — week-wise criticality counts or `/api/charts/vital-module-trend` — week-wise vital counts by module.
- **Report endpoints**: `/api/reports/aggregate` — group-wise aggregation for PDF and UI or `/api/reports/pdf` — generates a print-ready PDF (ReportLab).

---

## 🔄 Admin APIs
- **Mark closed (bulk)**: POST `/api/observations/close` → { "ids": [1,2,3] }
- **Mark resurfaced (bulk)**: POST `/api/observations/resurface` → { "ids": [4,5] }
- Get observations by date range: POST `/api/observations/range` → { "from_date":"2025-12-01", "to_date":"2025-12-31" }

---

## 🧾 How to generate the PDF
- Click View Reports → select date range → Generate PDF.
- Server produces a print-ready PDF and the browser auto-opens the print dialog.

---

## 🧩 Contribution, Customization & Roadmap
- Add Role-Based Access Control (RBAC) for admin actions.
- Add audit history table for status transitions (who changed what and when).
- Dockerise (optional) for consistent deployments.
- Add CSV/Excel exports and scheduled report emailing.

---

## 📝 Credits
- Author: Lt Cdr Mehta — Naval Dockyard, Mumbai
- Original Project: Navyojana ERP Monitoring Platform

---

## 🙋 Contact & Demo
For help with deployment, systemd unit examples, or PDF template tweaks — open an issue or contact the maintainer listed in the repo.

---

👉 **Navyojana turns operational noise into leadership-grade insight: one click to brief, one chart to spot trends, and auditable action trails to resolve issues faster. Deploy it tomorrow, brief senior leadership the day after.**
