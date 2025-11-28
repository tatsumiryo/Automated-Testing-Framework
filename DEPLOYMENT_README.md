# Voice Agent Testing Framework - Deployment Guide

## Project Overview

Automated testing and evaluation framework for healthcare AI voice agents using LLM-based quality assessment. The system evaluates multi-turn conversations across 6 healthcare-specific criteria and provides detailed insights with explanations.

**Key Features:**
- ✅ LLM-based evaluation using Google Gemini 2.5 Flash
- ✅ 6 comprehensive evaluation criteria
- ✅ Healthcare-specific assessment (safety, compliance, medical accuracy)
- ✅ CSV batch processing
- ✅ AWS DynamoDB storage
- ✅ Explainable results (strengths & improvements)

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                   SYSTEM ARCHITECTURE                        │
└─────────────────────────────────────────────────────────────┘

CSV File (Conversations)
        ↓
Python Script (csv_conversation_evaluator.py)
        ↓
Google Gemini API (LLM Evaluation)
        ↓
Evaluation Results (JSON with scores + reasoning)
        ↓
AWS DynamoDB (test_results table)
        ↓
Dashboard/Reports (View results)
```

---

## Prerequisites

### Required Accounts & Services
1. **AWS Account** with access to:
   - DynamoDB
   - IAM (for permissions)
   
2. **Google AI Account** for:
   - Gemini API key (free tier available)

3. **Python 3.9+** installed

---

## Step 1: AWS Setup

### 1.1 Create DynamoDB Tables

**Table 1: test_results** (Primary table for evaluations)

1. Go to AWS Console → DynamoDB → Tables → Create table
2. Configure:
   ```
   Table name: test_results
   Partition key: test_id (String)
   Sort key: (none)
   
   Table settings: Default settings
   ```
3. Click "Create table"

**Table 2: conversation_logs** (Optional - for logging)

1. Create another table:
   ```
   Table name: conversation_logs
   Partition key: test_id (String)
   Sort key: (none)
   ```

### 1.2 Set Up IAM Permissions

Create an IAM user or role with these permissions:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "dynamodb:PutItem",
        "dynamodb:GetItem",
        "dynamodb:Scan",
        "dynamodb:Query",
        "dynamodb:UpdateItem",
        "dynamodb:DeleteItem"
      ],
      "Resource": [
        "arn:aws:dynamodb:REGION:ACCOUNT_ID:table/test_results",
        "arn:aws:dynamodb:REGION:ACCOUNT_ID:table/conversation_logs"
      ]
    }
  ]
}
```

Replace:
- `REGION` with your AWS region (e.g., `us-east-1`)
- `ACCOUNT_ID` with your AWS account ID

### 1.3 Configure AWS Credentials

**Option A: AWS CLI Configuration**
```bash
aws configure
# Enter your AWS Access Key ID
# Enter your AWS Secret Access Key
# Enter region: us-east-1
# Enter output format: json
```

**Option B: Environment Variables**
```bash
export AWS_ACCESS_KEY_ID=your_access_key
export AWS_SECRET_ACCESS_KEY=your_secret_key
export AWS_DEFAULT_REGION=us-east-1
```

**Option C: EC2 Instance Role** (if deploying to EC2)
- Attach the IAM role with DynamoDB permissions to your EC2 instance

---

## Step 2: Get Gemini API Key

1. Go to: https://makersuite.google.com/app/apikey
2. Sign in with Google account
3. Click "Create API Key"
4. Copy the key (format: `AIzaSy...`)

**Note:** Free tier includes:
- 60 requests per minute
- 1 million tokens per day
- Sufficient for testing purposes

---

## Step 3: Project Setup

### 3.1 Clone/Download Project Files

Required files:
```
project/
├── csv_conversation_evaluator.py   # Main evaluation script
├── requirements.txt                # Python dependencies
├── .env.example                    # Environment variables template
├── conversations.csv               # Your conversation data
└── README.md                       # This file
```

### 3.2 Install Dependencies

```bash
# Create virtual environment (recommended)
python -m venv venv

# Activate virtual environment
# On Windows:
venv\Scripts\activate
# On Mac/Linux:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 3.3 Configure Environment Variables

1. Create `.env` file:
```bash
cp .env.example .env
```

2. Edit `.env` file:
```bash
# Gemini API Configuration
GEMINI_API_KEY=your_gemini_api_key_here

# AWS Configuration (optional if using AWS CLI)
AWS_ACCESS_KEY_ID=your_aws_access_key
AWS_SECRET_ACCESS_KEY=your_aws_secret_key
AWS_DEFAULT_REGION=us-east-1
```

**IMPORTANT:** Never commit `.env` to git!
```bash
echo ".env" >> .gitignore
```

---

## Step 4: Prepare Conversation Data

### 4.1 CSV Format

Create `conversations.csv` with this structure:

```csv
conversation_id,title,conversation_text
1,Urgent Chest Pain,"Bot: Hello, this is HealthCare Assistant...
Patient: I'm having chest pain...
Bot: I understand your concern..."
2,Appointment Booking,"Bot: Good morning...
Patient: I'd like to schedule..."
```

**CSV Requirements:**
- Header row: `conversation_id,title,conversation_text`
- `conversation_id`: Unique identifier (integer or string)
- `title`: Conversation scenario/title
- `conversation_text`: Full conversation with Bot/Patient turns
- Use quotes around conversation_text (it contains line breaks)
- UTF-8 encoding

### 4.2 Sample Data

See `sample_conversations.csv` for examples of properly formatted conversations.

---

## Step 5: Run the Evaluator

### 5.1 Basic Usage

```bash
python csv_conversation_evaluator.py
```

This will:
1. Read conversations from `conversations.csv`
2. Send each to Gemini for evaluation
3. Parse and validate results
4. Save to DynamoDB
5. Generate summary report

### 5.2 Expected Output

```
============================================================
🚀 CSV CONVERSATION EVALUATOR
============================================================
✅ Conversation Evaluator initialized with Gemini 2.5 Flash

============================================================
📁 PROCESSING CSV: conversations.csv
============================================================

============================================================
🤖 Evaluating: Urgent Triaging - Chest Pain
============================================================
📝 Conversation length: 823 characters
🔄 Sending to Gemini for evaluation...
📥 Received evaluation from Gemini

============================================================
📊 EVALUATION RESULTS
============================================================
✅ Overall Score: 94.50%

📋 Detailed Scores:
   intent_recognition: 98.00%
   response_correctness: 95.00%
   error_handling: 92.00%
   tone_appropriateness: 93.00%
   safety_compliance: 98.00%
   conversation_flow: 94.00%

💡 Overall Assessment: Excellent emergency triaging...

💪 Strengths:
   • Immediately recognized urgency
   • Appropriate 911 recommendation
   • Clear safety instructions

🔧 Areas for Improvement:
   • Could ask about existing conditions

============================================================

💾 Saved to DynamoDB: conv_1_1699876543210

[... continues for all conversations ...]

============================================================
📊 EVALUATION SUMMARY REPORT
============================================================

✅ Conversations Evaluated: 10
✅ Passed (≥80%): 9/10 (90.0%)
📈 Average Overall Score: 88.4%

📋 Average Scores by Criterion:
   intent_recognition: 91.2%
   response_correctness: 89.5%
   error_handling: 86.3%
   tone_appropriateness: 88.7%
   safety_compliance: 92.1%
   conversation_flow: 87.8%

🏆 Top Performing Conversations:
   1. Urgent Triaging - Chest Pain: 94.5%
   2. Pediatric Triaging - Child with Fever: 92.8%
   3. Routine Appointment Booking: 90.3%

============================================================
```

---

## Step 6: Verify Data in DynamoDB

### Option A: AWS Console

1. Go to AWS Console → DynamoDB → Tables
2. Click "test_results"
3. Click "Explore table items"
4. View evaluation records

Each record contains:
```
test_id: conv_1_xxx
conversation_title: "Urgent Chest Pain"
conversation_id: "1"
timestamp: "2025-11-08T17:09:18"
overall_score: 0.945
intent_recognition: 0.98
response_correctness: 0.95
error_handling: 0.92
tone_appropriateness: 0.93
safety_compliance: 0.98
conversation_flow: 0.94
passed: true
overall_assessment: "Excellent emergency triaging..."
strengths: ["Immediately recognized urgency", ...]
improvements: ["Could ask about existing conditions"]
```

### Option B: Python Script

```python
import boto3

dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
table = dynamodb.Table('test_results')
response = table.scan()

print(f"Total evaluations: {len(response['Items'])}")
for item in response['Items']:
    if item['test_id'].startswith('conv_'):
        print(f"{item['conversation_title']}: {float(item['overall_score'])*100:.0f}%")
```

---

## Configuration Options

### Evaluation Criteria Weights

Edit `csv_conversation_evaluator.py` to customize:

```python
weights = {
    "intent_recognition": 0.15,      # 15%
    "response_correctness": 0.25,    # 25%
    "error_handling": 0.15,          # 15%
    "tone_appropriateness": 0.15,    # 15%
    "safety_compliance": 0.20,       # 20%
    "conversation_flow": 0.10        # 10%
}
```

### Pass Threshold

Default: 80% overall score

```python
evaluation["passed"] = overall_score >= 0.80
```

### Gemini Model Settings

```python
generation_config = {
    "temperature": 0.3,        # Lower = more consistent
    "top_p": 0.95,
    "top_k": 40,
    "max_output_tokens": 4096  # Increase if responses truncate
}
```

---

## Troubleshooting

### Issue 1: "GEMINI_API_KEY not found"
**Solution:**
- Check `.env` file exists
- Verify `GEMINI_API_KEY=` has your actual key
- Run `python -c "import os; from dotenv import load_dotenv; load_dotenv(); print(os.getenv('GEMINI_API_KEY'))"` to test

### Issue 2: "DynamoDB access denied"
**Solution:**
- Verify IAM permissions
- Check AWS credentials are configured
- Ensure table names match (`test_results`)
- Verify region is correct (`us-east-1`)

### Issue 3: "JSON parsing error"
**Solution:**
- Check `max_output_tokens` is at least 4096
- Review Gemini API response in console output
- Verify system instructions are correctly formatted

### Issue 4: "Rate limit exceeded"
**Solution:**
- Gemini free tier: 60 requests/minute
- Script has 1-second delays between calls
- Increase delay: `time.sleep(2)` in code
- Or use paid tier for higher limits

### Issue 5: "CSV file not found"
**Solution:**
- Ensure `conversations.csv` is in same directory as script
- Check filename spelling
- Verify UTF-8 encoding

### Issue 6: Scores all 0.5 (fallback)
**Solution:**
- Check Gemini API key is valid
- Review console output for error messages
- Ensure internet connectivity
- Check Gemini API status

---

## Cost Estimates

### Gemini API (Free Tier)
- ✅ 60 requests/minute
- ✅ 1 million tokens/day
- ✅ Cost: **$0**

**For 100 conversations:**
- ~100 API calls
- ~200K tokens
- Cost: **Free** (within limits)

### AWS DynamoDB (Pay-as-you-go)
- ✅ 25 GB storage free tier
- ✅ 25 read/write capacity units free tier

**For 1000 evaluations:**
- Storage: <1 MB
- Reads/Writes: ~2000 operations
- Cost: **$0** (within free tier)

**Total Cost for Student Project: $0** ✅

---

## Production Deployment

### Option 1: EC2 Instance

1. Launch EC2 instance (Ubuntu 22.04, t2.micro)
2. Attach IAM role with DynamoDB permissions
3. Install Python and dependencies
4. Clone project
5. Set up `.env` with Gemini API key
6. Run evaluator as needed

### Option 2: AWS Lambda (Advanced)

For scheduled/automated evaluation:
1. Package code + dependencies as Lambda layer
2. Configure Lambda with DynamoDB permissions
3. Set Gemini API key in environment variables
4. Trigger via S3 upload or CloudWatch Events

### Option 3: Docker Container

```dockerfile
FROM python:3.9-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["python", "csv_conversation_evaluator.py"]
```

---

## Security Best Practices

### ✅ DO:
- Store API keys in `.env` file (not in code)
- Add `.env` to `.gitignore`
- Use IAM roles on EC2 (not hardcoded credentials)
- Regularly rotate API keys
- Use least-privilege IAM policies
- Enable DynamoDB encryption at rest

### ❌ DON'T:
- Commit API keys to git
- Share `.env` file
- Use root AWS credentials
- Store sensitive data in code
- Expose API keys in logs

---

## Monitoring & Maintenance

### Check Evaluation Quality
```python
# Get average scores
response = table.scan()
avg_score = sum(float(i['overall_score']) for i in response['Items']) / len(response['Items'])
print(f"Average: {avg_score:.2%}")
```

### Monitor API Usage
- Check Gemini API console for quota usage
- Set up CloudWatch alarms for DynamoDB capacity

### Regular Updates
- Keep dependencies updated: `pip install --upgrade -r requirements.txt`
- Monitor Gemini API for model updates
- Review and adjust evaluation criteria as needed

---

## Support & Documentation

### Gemini API Documentation
- https://ai.google.dev/docs

### AWS DynamoDB Documentation
- https://docs.aws.amazon.com/dynamodb/

### Project Repository
- Include link to your GitHub repository

---

## License

[Include your chosen open-source license here]

MIT License recommended for academic projects.

---

## Acknowledgments

- Google Gemini for LLM evaluation capabilities
- AWS for cloud infrastructure
- KeyReply for sample healthcare conversations

---

## Contact

**Project Author:** Matthew  
**Institution:** Singapore Institute of Technology  
**Course:** INF2006 - Cloud Computing and Big Data  
**Academic Year:** 2025

For questions or issues, please contact: [your-email@example.com]

---

## Appendix: System Requirements

### Minimum Requirements
- Python 3.9+
- 2 GB RAM
- 1 GB disk space
- Internet connection
- AWS account
- Google account (for Gemini API)

### Recommended Requirements
- Python 3.10+
- 4 GB RAM
- 5 GB disk space
- Stable internet connection

### Tested Environments
- ✅ Windows 10/11
- ✅ macOS 12+
- ✅ Ubuntu 20.04+
- ✅ AWS EC2 (Amazon Linux 2, Ubuntu)

---

**Last Updated:** November 8, 2025  
**Version:** 1.0.0
