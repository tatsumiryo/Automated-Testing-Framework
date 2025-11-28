# 🎤 AI Voice Agent Testing Framework

[![Python](https://img.shields.io/badge/Python-3.8+-blue)](https://www.python.org/) 
[![Flask](https://img.shields.io/badge/Flask-2.2+-orange)](https://flask.palletsprojects.com/) 
[![AWS](https://img.shields.io/badge/AWS-Cloud-orange)](https://aws.amazon.com/)
[![License](https://img.shields.io/badge/License-MIT-green)](LICENSE)

**Automated testing framework for healthcare AI voice agents** that evaluates performance across multiple user personas using LLM-based scoring and cloud-hosted dashboards. Built for KeyReply to ensure voice agent quality before production deployment.

**Institution:** Singapore Institute of Technology (SIT)  
**Industry Partner:** KeyReply  

---

## 📑 Table of Contents
1. [Project Overview](#-project-overview)
2. [Features](#-features)
3. [Quick Start](#-quick-start)
4. [Tech Stack](#%EF%B8%8F-tech-stack)
5. [Architecture](#%EF%B8%8F-architecture)
6. [DynamoDB Table Schemas](#%EF%B8%8F-dynamodb-table-schemas)
7. [Evaluation Metrics](#-evaluation-metrics)
8. [Usage](#-usage)
9. [AWS Infrastructure](#%EF%B8%8F-aws-infrastructure)
10. [Common Issues](#-common-issues)
11. [Cost & Resources](#-cost--resources)
12. [Team & Acknowledgments](#-team--acknowledgments)
13. [Security & License](#-security--license)


---

## 📝 Project Overview
This framework enables developers to evaluate healthcare AI voice agents across multiple personas (frustrated, elderly, non-native speakers, etc.), using LLM evaluation, automated scoring, and interactive dashboards.

**Key Capabilities:**
- Persona-based conversation evaluation
- LLM evaluation using **Google Gemini 2.5 Flash**
- Automated scoring on 6 metrics + overall weighted score
- Secure login & signup (JWT + bcrypt)
- Cloud deployment (AWS EC2 + DynamoDB)
- Real-time analytics dashboard
- Voice integration (ElevenLabs text-to-speech)

---

## 🚀 Features

### Conversation Evaluation (LLM-Powered)
- CSV file upload with 3 columns: `conversation_id`, `conversation_title`, `conversation`
- Gemini 2.5 Flash evaluation for 6 criteria:
  1. Intent Recognition
  2. Response Correctness
  3. Error Handling
  4. Tone Appropriateness
  5. Safety & Compliance
  6. Conversation Flow
- Generates:
  - 0–100 normalized score per metric
  - Overall weighted score
  - Strengths & improvement suggestions
  - Overall assessment
- Fallback to **mock evaluator** if no API key is provided

### User Authentication
- DynamoDB + JWT + bcrypt
- Signup with validations
- Login with token issuance (24h expiry)
- Token-based access control for API routes
- Persistent login tracking (`last_login` timestamp)

---

## 🚀 Quick Start

<details>
<summary>Click to expand</summary>

### Prerequisites
- Python 3.8+
- AWS Account (CLI configured)
- Terraform 1.5+
- ElevenLabs API key
- **Google Gemini API Key**  

**How to retrieve Gemini API Key:**  
1. Sign in to your Google Cloud account.  
2. Go to [Google Gemini API console](https://ai.google.dev/gemini-api/docs/api-key).  
3. Create a new project (if none exists).  
4. Enable the Gemini API and generate a **secret API key**.  
5. Store the key securely in your `.env` file.

### Clone & Install
```bash
git clone <your-repo-url>
cd voice-agent-testing
pip install -r requirements.txt
```

### Configure Environment
```bash
# .env file
GEMINI_API_KEY=your_gemini_api_key_here
AWS_REGION=us-east-1
```

### Run Locally
```bash
python3 app.py
```
Server: `http://localhost:5000`

### Cloud Version
- [Production](http://52.23.188.49:5000)
- [Analytics Dashboard](http://52.23.188.49:5000/static/index.html)

</details>

---

## 🛠️ Tech Stack

<details>
<summary>Click to expand</summary>

| Component      | Technology              | Purpose                        |
| -------------- | --------------------- | ------------------------------ |
| Compute        | AWS EC2 (t3.micro)      | Runs Flask app                 |
| Database       | AWS DynamoDB            | Stores evaluations & user data |
| Storage        | AWS S3                  | Scripts, logs, results         |
| Backend        | Flask (Python 3.8+)     | API server & routing           |
| Authentication | JWT + bcrypt            | Secure user login              |
| LLM            | Google Gemini 2.5 Flash | AI conversation evaluation     |
| Voice API      | ElevenLabs              | Text-to-speech integration     |
| Monitoring     | AWS CloudWatch          | System health tracking         |
| IaC            | Terraform 1.5+          | Infrastructure automation      |

</details>

---

## 🏗️ Architecture

<details>
<summary>Click to expand</summary>
  
### Cloud Infrastructure
- Compute: AWS EC2 (t3.micro)
- Database: DynamoDB (`test_results`, `users`)
- Security: IAM roles & security groups (least privilege)
- Monitoring: CloudWatch dashboards & alarms
- IaC: Terraform automation

### Application Components
- Flask-based Voice Agent API (healthcare logic)
- Automated persona-based testing framework
- Real-time analytics dashboard
- Voice Integration via ElevenLabs API

```
User Upload CSV → Flask API (EC2) → Gemini LLM Evaluation
                        ↓
                  DynamoDB Storage
                        ↓
                  S3 Storage (Results)
                        ↓
                  Analytics Dashboard (Visualization)
```

</details>

---

## 🗄️ DynamoDB Table Schemas

<details>
<summary>Click to expand</summary>

### `test_results`
| Attribute             | Type   | Description                         |
| --------------------- | ------ | ----------------------------------- |
| conversation_id        | String | Unique ID of conversation           |
| conversation_title     | String | Title of the conversation           |
| improvements           | String | Suggested improvements             |
| overall_assessment     | String | Pass/Fail or textual assessment     |
| overall_score          | Number | Weighted overall score              |
| scores                 | Map    | Individual metric scores            |
| strengths              | String | Notable strengths of the agent     |
| timestamp              | String | Evaluation timestamp                |

### `users`
| Attribute    | Type   | Description                  |
| ------------ | ------ | ---------------------------- |
| email        | String | User login email             |
| created_at   | String | Account creation timestamp   |
| last_login   | String | Last login timestamp         |
| name         | String | User's full name             |
| password     | String | Hashed password (bcrypt)     |

</details>

---

## 📊 Evaluation Metrics

<details>
<summary>Click to expand</summary>

| Metric               | Weight | Description                        |
| -------------------- | ------ | ---------------------------------- |
| Intent Recognition   | 15%    | Did agent understand user's needs? |
| Response Correctness | 25%    | Accurate and helpful responses     |
| Error Handling       | 15%    | Handles unclear queries gracefully |
| Tone Appropriateness | 15%    | Professional, empathetic tone      |
| Safety & Compliance  | 20%    | Follows healthcare guidelines      |
| Conversation Flow    | 10%    | Natural, coherent conversation     |

**Overall Score:** Weighted average  
**Pass Threshold:** 80%

</details>

---

## 📝 Usage

<details>
<summary>Click to expand</summary>

### Step 1: Prepare CSV
```csv
conversation_id,conversation_title,conversation
1,Urgent Chest Pain,"Bot: Hello, how can I help?
Patient: I have chest pain
Bot: I'll connect you to emergency services immediately"
```

### Step 2: Sign Up / Log In
* Receive JWT token valid 24h

### Step 3: Upload & Evaluate
* Click "Upload CSV" → Select file → Click "Evaluate"

### Step 4: View Results
* Main Dashboard: stats, pass/fail rates
* Analytics Dashboard: trends, conversation flow

</details>

---

## 🗄️ AWS Infrastructure

<details>
<summary>Click to expand</summary>
  
**Compute:**  
- **EC2 t3.micro** instance running the Flask application  
- Security: Security Groups allowing HTTP/HTTPS, IAM role with least-privilege access  

**Database:**  
- **DynamoDB** tables:  
  - `test_results` (stores conversation evaluations)
  - `users` (stores authentication and user data)  

**Storage:**  
- **S3 Bucket** for storing logs, uploaded CSVs, and evaluation results  

**Monitoring:**  
- **CloudWatch** dashboards for system health, logs, and alarms  

**IAM & Security:**  
- IAM roles assigned to EC2 with least-privilege permissions  
- Credentials stored securely in `.env` or AWS Secrets Manager  
- No sensitive information committed to GitHub  

**Infrastructure as Code (IaC):**  
- **Terraform 1.5+** used to deploy EC2, DynamoDB tables, S3 buckets, and IAM roles

</details>

---

## 🐛 Common Issues

<details>
<summary>Click to expand</summary>

* **GEMINI_API_KEY missing:** Verify `.env` and retrieve API key from Google Gemini console  
* **DynamoDB access denied:** Check IAM & AWS credentials  
* **CSV Upload Fails:** Ensure 3 columns, UTF-8, quotes around conversation text

</details>

---

## 💰 Cost & Resources

<details>
<summary>Click to expand</summary>
  
* Gemini API (Google Cloud): Free tier – 60 requests/min, 1M tokens/day  
* DynamoDB: Free tier (25 GB storage + read/write capacity units)  
* EC2 t3.micro: Free tier for first 12 months (750 hours/month)  
* S3: Free tier (5 GB storage, limited requests)  

**Note:** Costs are $0 only if usage stays within Free Tier limits. Exceeding these limits will incur charges.

</details>

## 👥 Team & Acknowledgments

<details>
<summary>Click to expand</summary>

**SIT Students** | KeyReply Partner  
Powered by Google Gemini, AWS, ElevenLabs

</details>

## 🔒 Security & License

<details>
<summary>Click to expand</summary>

* **Do NOT commit:** `.env`, AWS credentials, private keys  
* Add to `.gitignore`: `.env`, `*.pem`, `aws-credentials.txt`  
* **License:** MIT (Educational Use)

</details>

**Last Updated:** November 28, 2025  
**Version:** 2.0.2
