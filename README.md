# Parkinson's Disease Detection & Medical Assistant

An AI-powered web application for Parkinson's disease diagnosis assistance using MRI brain scans, Grad-CAM visual explainability, and an integrated AI Medical Assistant.

---

## 🌟 Key Features

- **MRI Deep Learning Classification**: Uses a trained **DenseNet121** model to detect Parkinson's disease indicators from uploaded brain MRI scans.
- **Grad-CAM Explainability**: Visualizes class-activation heatmaps superimposed on original MRI scans to highlight anatomical regions contributing to the prediction.
- **AI Medical Assistant**: An intelligent chatbot powered by LLM (DeepSeek / OpenRouter) to provide information about symptoms, disease progression, treatments, and nearby neurology centers.
- **User Authentication & Session Management**: Secure user registration and login with token-based authentication and password hashing.
- **Scan History Tracking**: Automatically archives past MRI scans, predictions, confidence scores, and heatmaps for authenticated users.

---

## 📂 Project Structure

```text
parkinsons_web/
├── app.py                      # Main Flask application & API endpoints
├── database.py                 # SQLAlchemy database models (User, ScanHistory)
├── CP_DenseNet121_Final.h5     # Trained DenseNet121 Keras model
├── requirements.txt            # Python dependencies
├── dummy_mri.jpg               # Sample MRI image for testing
├── test_api.py                 # API test script
├── .env.example                # Environment variables template
├── .gitignore                  # Git ignore rules
├── templates/
│   └── index.html              # Frontend user interface
└── static/
    ├── app.js                  # Frontend interactions & API client
    ├── style.css               # Styling and UI themes
    ├── bg.png                  # Background asset
    └── uploads/                # Temporary uploaded & Grad-CAM images (ignored by git)
```

---

## 🚀 Getting Started

### 1. Prerequisites

- Python 3.9 – 3.12
- Git

### 2. Installation

1. **Clone the repository:**
   ```bash
   git clone https://github.com/<your-username>/parkinsons_web.git
   cd parkinsons_web
   ```

2. **Create and activate a virtual environment (recommended):**
   ```bash
   # Windows
   python -m venv venv
   .\venv\Scripts\activate

   # Linux / macOS
   python3 -m venv venv
   source venv/bin/activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure Environment Variables:**
   Copy `.env.example` to `.env` and insert your DeepSeek or OpenRouter API key:
   ```bash
   copy .env.example .env
   ```
   Open `.env` and set:
   ```env
   DEEPSEEK_API_KEY=your_actual_api_key_here
   ```

### 3. Running the Application

Start the Flask server:
```bash
python app.py
```

The web application will be accessible at:
```text
http://127.0.0.1:5000
```

---

## 🧪 Testing the API

Run the automated test script to verify registration, login, and MRI prediction endpoints:
```bash
python test_api.py
```

---

## 🔒 Security & Privacy Notice

- API keys and local database files (`*.db`) are ignored by version control.
- Never commit active API keys to public repositories.

---

## 📄 License

This project is open-source and available under the [MIT License](LICENSE).
