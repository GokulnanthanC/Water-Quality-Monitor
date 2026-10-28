# Water Quality Monitor - Completed Features Specification

> **Project Overview**: A comprehensive full-stack Water Quality Monitoring & Pollution Reporting platform built with FastAPI (Python) and React + Vite (Tailwind CSS / Leaflet / Recharts). It integrates Open Government Data (OGD) from the Central Pollution Control Board (CPCB), geospatial monitoring stations, citizen reporting with photo verification, NGO initiatives, and an interactive analytics dashboard.

---

## 📋 Feature Summary Matrix

| Module | Features Completed | Target Roles |
| :--- | :--- | :--- |
| **Authentication & RBAC** | JWT Auth, bcrypt password hashing, 4 distinct roles, Admin user creation | Citizen, NGO, Authority, Admin |
| **Interactive Map** | React-Leaflet GIS map, 40+ monitoring stations, status popups & diary | All Users |
| **Live Water Analytics** | OGD India API integration, 40-station trends, Line & Radar charts | All Users |
| **Pollution Reporting** | Photo upload with validation, auto-station detect, report modal viewer | Citizen (Submit) |
| **Report Verification** | Authority approval/rejection workflow, status transition tracking | Authority, NGO, Admin |
| **Admin Management** | User registration portal, report purging with disk cleanup, role control | Admin |
| **Central Dashboard** | System stats cards, Report/Alert status pie charts, parameter box plots | All Users |
| **NGO Community Hub** | NGO project submission, contact listings, project portfolio display | NGO |

---

## 🚀 Detailed Breakdown of Completed Features

### 1. 🔐 Authentication & Role-Based Access Control (RBAC)
- **Four Distinct User Roles**:
  - `citizen`: Submit pollution reports, view live water quality data, explore monitoring map.
  - `authority`: Inspect, verify, or reject pending pollution reports from citizens.
  - `ngo`: Moderate/verify reports, publish and manage NGO community water projects.
  - `admin`: Full administrative control, create/register new users across all roles, delete reports.
- **Security & Password Hashing**:
  - Implemented secure password hashing via `passlib` with `bcrypt` (12 rounds).
  - Schema-level password strength enforcement (minimum 8 characters, requiring uppercase, lowercase, and numeric characters).
- **JWT (JSON Web Token) Workflow**:
  - Signed tokens generated with expiration handling (`python-jose`).
  - Frontend Axios interceptors automatically inject `Bearer <token>` headers into every API request.
  - Automatic session expiry detection with redirection to login on `401 Unauthorized`.
- **Pre-seeded Admin User**:
  - Application auto-seeds default admin credentials (`admin123@gmail.com`) on startup.
- **Frontend Role Protection**:
  - `ProtectedRoute` wrapper guarding private views and restricting specific routes (e.g. `/register` to `admin`, `/ngo` to `ngo`).
  - Interactive login view with role selector and password visibility toggle.

---

### 2. 🗺️ Geospatial Monitoring Station Map
- **Interactive Leaflet Map (`react-leaflet`)**:
  - Full-screen and embedded map view supporting smooth pan, zoom, and tile rendering via OpenStreetMap.
- **Monitoring Station Dataset**:
  - 40+ pre-configured CPCB water quality monitoring stations spanning major river basins across multiple Indian states (Bihar, Haryana, Jharkhand, Uttarakhand, Uttar Pradesh, West Bengal).
  - Stations include exact geographic coordinates (latitude & longitude), river/canal identifiers, and territory names.
- **Station Diary & Status Popups**:
  - Clicking any station marker displays rich metadata including site name, status remarks, and Force Majeure logs (flood events, technical issues, maintenance).

---

### 3. 📈 Live Water Quality Monitoring & Data Analytics
- **Open Government Data (OGD) Integration**:
  - Backend `ogd_service.py` connects to `data.gov.in` surface water quality datasets.
  - Dynamic fallback generating realistic chronologically-ordered continuous time-series data for all 40+ master stations when API limits or network issues occur.
- **Monitored Environmental Parameters**:
  - **pH Level** (Acidity/Alkalinity)
  - **Dissolved Oxygen (DO)** (mg/L)
  - **Turbidity** (NTU)
- **Interactive Station Selector**:
  - Dropdown selector enabling real-time switching between stations.
- **Dual Visualizations**:
  - **Trend Line Chart**: Responsive multi-line chart with glowing drop shadows, custom tooltips, grid lines, and 12-hour AM/PM formatted time axes.
  - **Radar Chart**: 3-axis radar chart displaying the instant snapshot of environmental indicators.

---

### 4. 📸 Citizen Pollution Reporting & Evidence Upload
- **Smart Pollution Report Submission Form (`/report`)**:
  - **Station Auto-Fill**: Selecting the nearest monitoring station automatically populates the location and auto-detects the water source category (River, Canal, Lake, Pond, Stream, etc.).
  - **Detailed Description**: Validated text area (10 to 1,000 characters).
  - **Photo Upload Verification**: Supports image uploads (JPG, PNG, GIF, WebP) with a 5MB size limit.
- **Safe Media Storage**:
  - Uploaded photos are verified, renamed with secure UUIDs, and served statically from `/uploads`.
- **Public & Role-Filtered Report Feed (`/reports`)**:
  - Responsive grid layout presenting report cards with photo thumbnails, location, source, and color-coded status badges (`pending`, `verified`, `rejected`).
- **Interactive Report Modal**:
  - Click-to-view modal with full-size evidence image and complete submission metadata.

---

### 5. ⚖️ Authority Verification & Moderation Workflow
- **Report Verification & Rejection**:
  - Authorities, NGOs, and Admins can act on `pending` reports with **Verify** (green) or **Reject** (red) actions.
  - Status changes update the database and reflect immediately across the dashboard and reports feed.
- **Admin Report Deletion**:
  - Admins can permanently delete reports, which automatically removes the record from PostgreSQL/SQLite and purges the associated image file from disk.

---

### 6. 📊 Central System Dashboard (`/dashboard`)
- **Key Metric KPI Cards**:
  - Total Monitoring Stations count.
  - Total Water Quality Readings collected.
  - Average Readings per Station.
  - Average User Reports per Station.
- **Distribution Visualizations**:
  - **Alert Status Pie Chart**: Visual breakdown of active vs. resolved environmental alerts.
  - **Report Status Pie Chart**: Proportion of pending, verified, and rejected citizen reports.
  - **Parameter Statistics (Box Plot Range Simulation)**: Minimum, Median, and Maximum ranges for core parameters.
- **Recent Feeds**:
  - Latest 3 system pollution alerts with severity levels (Critical, High, Warning).
  - Latest 3 citizen reports with live status indicators.
- **In-Memory Performance Cache**:
  - Dashboard endpoint features a 30-second cache to optimize database query throughput.

---

### 7. 🤝 NGO Community Projects Portal (`/ngo`)
- **Project Publishing Form**:
  - NGOs can publish water conservation and cleanup initiatives specifying Project Name, Contact Email, and Project Description.
- **Project Showcase Feed**:
  - Grid view listing all active NGO initiatives for community visibility and collaboration.

---

### 8. 🛡️ User Management Portal (`/register`)
- **Admin-Controlled Account Creation**:
  - Dedicated administrative view to provision accounts for new citizens, NGO representatives, or government authorities.
  - Form validation with live password requirement feedback.

---

## 🛠️ Tech Stack & Architecture

### Backend
- **Framework**: FastAPI (Python 3.10+)
- **ORM / Database**: SQLAlchemy with PostgreSQL / SQLite compatibility
- **Authentication**: OAuth2 Password Flow + JWT (`python-jose`, `passlib[bcrypt]`)
- **Validation**: Pydantic v2 schemas with custom validators
- **External Integration**: Open Government Data (OGD) REST API (`data.gov.in`)

### Frontend
- **Framework**: React 18 with Vite
- **Routing**: React Router DOM v6
- **Styling**: Tailwind CSS & Vanilla CSS with modern Dark Mode slate aesthetics
- **Mapping**: Leaflet & React-Leaflet
- **Charts & Visuals**: Recharts (Line Charts, Radar Charts, Pie Charts)
- **Icons**: Lucide React
