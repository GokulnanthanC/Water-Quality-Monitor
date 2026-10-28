# Water Quality Monitoring & Pollution Reporting System

An end-to-end full-stack water quality monitoring, pollution reporting, and environmental analytics platform.

## 📄 Feature Documentation
For the complete, comprehensive list of implemented features and modules, please see [FEATURES_COMPLETED.md](file:///c:/Users/gokul/OneDrive/ドキュメント/Water-Quality-Monitor/FEATURES_COMPLETED.md).

---

## 🌟 Highlights
- **Role-Based Access Control (RBAC)**: Supports `citizen`, `ngo`, `authority`, and `admin` roles with JWT security.
- **Geospatial Map**: Interactive Leaflet map plotting 40+ monitoring stations across Indian river basins with status diaries.
- **Real-Time Analytics**: CPCB / Open Government Data (OGD) integration for pH, Dissolved Oxygen (DO), and Turbidity with Recharts line and radar trend visualizations.
- **Citizen Incident Reporting**: Report submission with photo evidence upload, station auto-fill, and file validation.
- **Verification Workflow**: Authority and NGO review pipeline to verify or reject reported pollution events.
- **System Dashboard**: High-level statistical KPI cards, alert/report status distribution pie charts, parameter box plots, and live activity feeds.
- **NGO Project Hub**: Portal for NGOs to publish and manage community water conservation projects.

---

## 🚀 Quickstart

### Backend
```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```
Interactive API documentation available at `http://localhost:8000/docs`.

### Frontend
```bash
cd frontend
npm install
npm run dev
```
Access the application at `http://localhost:5173`.