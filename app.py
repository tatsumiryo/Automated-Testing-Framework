"""
Flask Backend for AI Voice Agent Testing Dashboard - FIXED VERSION
Now with DynamoDB Authentication and CSV Evaluation Integration
"""

from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import boto3
from decimal import Decimal
import json
import pandas as pd
from datetime import datetime, timedelta
import os
import subprocess
import bcrypt
import jwt
from functools import wraps

app = Flask(__name__, static_folder='static')
CORS(app)

# ==================== Configuration ====================

AWS_REGION = 'us-east-1'
DYNAMODB_TABLE = 'test_results'
USERS_TABLE = 'users'

SECRET_KEY = os.environ.get('SECRET_KEY', 'matthew-keyreply-secretkey')
JWT_EXPIRATION_HOURS = 24

dynamodb = boto3.resource('dynamodb', region_name=AWS_REGION)
table = dynamodb.Table(DYNAMODB_TABLE)
users_table = dynamodb.Table(USERS_TABLE)

# ==================== Helper Functions ====================

class DecimalEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Decimal):
            return float(obj)
        return super().default(obj)

def hash_password(password):
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')

def verify_password(password, hashed):
    return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))

def generate_token(email, name):
    payload = {
        'email': email,
        'name': name,
        'exp': datetime.utcnow() + timedelta(hours=JWT_EXPIRATION_HOURS)
    }
    return jwt.encode(payload, SECRET_KEY, algorithm='HS256')

def verify_token(token):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=['HS256'])
        return payload
    except (jwt.ExpiredSignatureError, jwt.InvalidTokenError):
        return None

def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get('Authorization')
        if not token:
            return jsonify({'success': False, 'error': 'Token missing'}), 401
        if token.startswith('Bearer '):
            token = token[7:]
        payload = verify_token(token)
        if not payload:
            return jsonify({'success': False, 'error': 'Invalid token'}), 401
        request.user = payload
        return f(*args, **kwargs)
    return decorated

# ==================== Authentication Routes ====================

@app.route('/')
def index():
    return send_from_directory('static', 'login.html')

@app.route('/dashboard')
def dashboard():
    return send_from_directory('static', 'index.html')

@app.route('/api/auth/signup', methods=['POST'])
def signup():
    try:
        data = request.get_json()
        name = data.get('name', '').strip()
        email = data.get('email', '').strip().lower()
        password = data.get('password', '')

        if not name or not email or not password:
            return jsonify({'success': False, 'error': 'All fields are required'}), 400
        if '@' not in email or '.' not in email:
            return jsonify({'success': False, 'error': 'Invalid email format'}), 400
        if len(password) < 8:
            return jsonify({'success': False, 'error': 'Password must be at least 8 characters'}), 400
        if not any(c.isupper() for c in password):
            return jsonify({'success': False, 'error': 'Password must contain at least one uppercase letter'}), 400
        if not any(c.islower() for c in password):
            return jsonify({'success': False, 'error': 'Password must contain at least one lowercase letter'}), 400
        if not any(c.isdigit() for c in password):
            return jsonify({'success': False, 'error': 'Password must contain at least one number'}), 400

        response = users_table.get_item(Key={'email': email})
        if 'Item' in response:
            return jsonify({'success': False, 'error': 'Email already registered'}), 409

        hashed_password = hash_password(password)
        users_table.put_item(
            Item={
                'email': email,
                'name': name,
                'password': hashed_password,
                'created_at': datetime.utcnow().isoformat(),
                'last_login': datetime.utcnow().isoformat()
            }
        )
        token = generate_token(email, name)
        print(f"✅ New user created: {email}")
        return jsonify({'success': True, 'access_token': token, 'user': {'email': email, 'name': name}}), 201

    except Exception as e:
        print(f"❌ Signup error: {str(e)}")
        return jsonify({'success': False, 'error': 'Server error during signup'}), 500

@app.route('/api/auth/login', methods=['POST'])
def login():
    try:
        data = request.get_json()
        email = data.get('email', '').strip().lower()
        password = data.get('password', '')

        if not email or not password:
            return jsonify({'success': False, 'error': 'Email and password required'}), 400

        response = users_table.get_item(Key={'email': email})
        if 'Item' not in response:
            return jsonify({'success': False, 'error': 'Invalid email or password'}), 401

        user = response['Item']
        if not verify_password(password, user['password']):
            return jsonify({'success': False, 'error': 'Invalid email or password'}), 401

        users_table.update_item(
            Key={'email': email},
            UpdateExpression='SET last_login = :time',
            ExpressionAttributeValues={':time': datetime.utcnow().isoformat()}
        )

        token = generate_token(email, user['name'])
        print(f"✅ User logged in: {email}")
        return jsonify({'success': True, 'access_token': token, 'user': {'email': email, 'name': user['name']}})

    except Exception as e:
        print(f"❌ Login error: {str(e)}")
        return jsonify({'success': False, 'error': 'Server error during login'}), 500

@app.route('/api/auth/verify', methods=['GET'])
@token_required
def verify():
    return jsonify({'success': True, 'user': request.user})

@app.route('/api/auth/logout', methods=['POST'])
@token_required
def logout():
    return jsonify({'success': True, 'message': 'Logged out successfully'})

# ==================== Dashboard API Routes (FIXED) ====================

@app.route('/api/evaluations', methods=['GET'])
@token_required
def get_evaluations():
    """Get all evaluations from DynamoDB - CORRECTED ENDPOINT"""
    try:
        response = table.scan()
        items = response.get('Items', [])
        
        evaluations = []
        for item in items:
            # Handle both nested and flat score structures for backward compatibility
            scores = item.get('scores', {})
            if not scores:
                # Build nested structure from flat fields if needed
                scores = {
                    'intent_recognition': float(item.get('intent_recognition', 0)),
                    'response_correctness': float(item.get('response_correctness', 0)),
                    'error_handling': float(item.get('error_handling', 0)),
                    'tone_appropriateness': float(item.get('tone_appropriateness', 0)),
                    'safety_compliance': float(item.get('safety_compliance', 0)),
                    'conversation_flow': float(item.get('conversation_flow', 0))
                }
            else:
                # Convert Decimal to float for nested structure
                scores = {k: float(v) for k, v in scores.items()}
            
            evaluation = {
                'conversation_id': item.get('conversation_id', ''),
                'title': item.get('conversation_title', 'Unknown'),
                'timestamp': item.get('timestamp', ''),
                'overall_score': float(item.get('overall_score', 0)),
                'scores': scores,
                'strengths': item.get('strengths', []),
                'improvements': item.get('improvements', []),
                'overall_assessment': item.get('overall_assessment', '')
            }
            evaluations.append(evaluation)
        
        # Sort by timestamp (most recent first)
        evaluations.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
        
        print(f"📊 Retrieved {len(evaluations)} evaluations")
        
        return jsonify({
            'success': True,
            'count': len(evaluations),
            'evaluations': evaluations
        })
        
    except Exception as e:
        print(f"❌ Error fetching evaluations: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/evaluation/<conversation_id>', methods=['GET'])
@token_required
def get_evaluation(conversation_id):
    """Get a specific evaluation by conversation_id"""
    try:
        response = table.get_item(Key={'conversation_id': conversation_id})
        
        if 'Item' not in response:
            return jsonify({
                'success': False,
                'error': 'Evaluation not found'
            }), 404
        
        item = response['Item']
        
        # Handle nested scores structure
        scores = item.get('scores', {})
        if isinstance(scores, dict):
            scores = {k: float(v) for k, v in scores.items()}
        
        evaluation = {
            'conversation_id': item.get('conversation_id', ''),
            'title': item.get('conversation_title', 'Unknown'),
            'timestamp': item.get('timestamp', ''),
            'overall_score': float(item.get('overall_score', 0)),
            'scores': scores,
            'strengths': item.get('strengths', []),
            'improvements': item.get('improvements', [])
        }
        
        return jsonify({
            'success': True,
            'evaluation': evaluation
        })
        
    except Exception as e:
        print(f"❌ Error fetching evaluation: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/evaluate', methods=['POST'])
@token_required
def evaluate_conversations():
    """Upload CSV file and trigger evaluation - FIXED VERSION"""
    try:
        if 'file' not in request.files:
            return jsonify({'success': False, 'error': 'No file provided'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'success': False, 'error': 'Empty filename'}), 400
        
        # Accept both CSV and TXT files
        if not (file.filename.endswith('.csv') or file.filename.endswith('.txt')):
            return jsonify({'success': False, 'error': 'File must be CSV or TXT'}), 400

        upload_path = '/tmp/uploaded_conversations.csv'
        file.save(upload_path)
        print(f"✅ File uploaded: {file.filename}")

        # Run the csv_conversation_evaluator.py script
        python_exec = 'python3'
        script_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'csv_conversation_evaluator.py')
        
        # Check if script exists
        if not os.path.exists(script_path):
            return jsonify({'success': False, 'error': f'Evaluator script not found at {script_path}'}), 500
        
        print(f"🔄 Running evaluator: {python_exec} {script_path} {upload_path}")
        
        result = subprocess.run(
            [python_exec, script_path, upload_path],
            capture_output=True, 
            text=True, 
            timeout=120
        )

        # Debug output
        print(f"📊 Return code: {result.returncode}")
        if result.stderr:
            print(f"📋 STDERR:\n{result.stderr}")
        print(f"📄 STDOUT length: {len(result.stdout)} characters")

        # Check if evaluation failed
        if result.returncode != 0:
            error_msg = f"Evaluator script failed: {result.stderr}"
            print(f"❌ {error_msg}")
            return jsonify({'success': False, 'error': error_msg}), 500

        # Check if stdout is empty
        if not result.stdout.strip():
            error_msg = f"Evaluator returned empty output. STDERR: {result.stderr}"
            print(f"❌ {error_msg}")
            return jsonify({'success': False, 'error': 'Evaluator returned no data'}), 500

        # Parse JSON output from evaluator
        try:
            # Clean up any potential whitespace
            json_str = result.stdout.strip()
            
            # Try to find JSON array start
            if '[' not in json_str:
                print(f"❌ No JSON array found in output")
                return jsonify({'success': False, 'error': 'Invalid evaluator output format'}), 500
            
            # Extract JSON array
            start_idx = json_str.find('[')
            end_idx = json_str.rfind(']') + 1
            
            if start_idx == -1 or end_idx == 0:
                print(f"❌ Could not find valid JSON array boundaries")
                return jsonify({'success': False, 'error': 'Invalid JSON structure'}), 500
            
            json_str = json_str[start_idx:end_idx]
            print(f"✂️ Extracted JSON (length {len(json_str)})")
            
            evaluations = json.loads(json_str)
            print(f"✅ Successfully parsed {len(evaluations)} evaluations")
            
            if not isinstance(evaluations, list):
                print(f"❌ Parsed data is not a list: {type(evaluations)}")
                return jsonify({'success': False, 'error': 'Evaluator returned invalid data structure'}), 500
            
            if len(evaluations) == 0:
                return jsonify({'success': False, 'error': 'No conversations were evaluated. Check CSV format.'}), 400
            
            # Store in DynamoDB with CORRECT STRUCTURE
            successful_inserts = 0
            failed_inserts = 0
            
            for eval_item in evaluations:
                try:
                    # Get scores dict (already in 0-100 format from fixed evaluator)
                    scores = eval_item.get('scores', {})
                    
                    # Convert scores to Decimal for DynamoDB
                    scores_decimal = {
                        k: Decimal(str(v)) for k, v in scores.items()
                    }
                    
                    # Build DynamoDB item with NESTED scores structure
                    item = {
                        'conversation_id': eval_item.get('conversation_id', 'unknown'),
                        'conversation_title': eval_item.get('conversation_title', 'Untitled'),
                        'timestamp': datetime.utcnow().isoformat(),
                        'overall_score': Decimal(str(eval_item.get('overall_score', 0))),
                        'scores': scores_decimal,  # NESTED structure - this is key!
                        'strengths': eval_item.get('strengths', []),
                        'improvements': eval_item.get('improvements', []),
                        'overall_assessment': eval_item.get('overall_assessment', '')
                    }
                    
                    table.put_item(Item=item)
                    successful_inserts += 1
                    print(f"✅ Stored: {item['conversation_id']} - {item['conversation_title']}")
                    
                except Exception as e:
                    failed_inserts += 1
                    print(f"❌ Failed to insert evaluation: {e}")
                    import traceback
                    traceback.print_exc()

            print(f"✅ Successfully stored {successful_inserts}/{len(evaluations)} evaluations")
            
            return jsonify({
                'success': True, 
                'message': f'Successfully processed {len(evaluations)} conversations', 
                'count': len(evaluations),
                'stored_count': successful_inserts,
                'failed_count': failed_inserts
            })
            
        except json.JSONDecodeError as e:
            error_msg = f"JSON parsing failed: {str(e)}"
            print(f"❌ {error_msg}")
            print(f"Output preview: {result.stdout[:500]}")
            return jsonify({
                'success': False, 
                'error': f'Invalid JSON from evaluator: {str(e)}',
                'debug_output': result.stdout[:500]
            }), 500

    except subprocess.TimeoutExpired:
        print("❌ Evaluation timed out")
        return jsonify({'success': False, 'error': 'Evaluation timed out after 120 seconds'}), 500
    except Exception as e:
        print(f"❌ Error during evaluation: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/stats', methods=['GET'])
@token_required
def get_statistics():
    """Get overall statistics across all evaluations"""
    try:
        response = table.scan()
        items = response.get('Items', [])
        
        if not items:
            return jsonify({
                'success': True,
                'stats': {
                    'total_evaluations': 0,
                    'average_score': 0,
                    'pass_rate': 0
                }
            })
        
        # Calculate statistics
        total = len(items)
        scores = [float(item.get('overall_score', 0)) for item in items]
        average_score = sum(scores) / total if total > 0 else 0
        pass_count = sum(1 for score in scores if score >= 75)
        pass_rate = (pass_count / total * 100) if total > 0 else 0
        
        # Calculate criteria averages
        criteria_sums = {
            'intent_recognition': 0,
            'response_correctness': 0,
            'error_handling': 0,
            'tone_appropriateness': 0,
            'safety_compliance': 0,
            'conversation_flow': 0
        }
        
        for item in items:
            scores_dict = item.get('scores', {})
            for criterion in criteria_sums:
                criteria_sums[criterion] += float(scores_dict.get(criterion, 0))
        
        criteria_averages = {
            criterion: round((total_score / total), 2) if total > 0 else 0
            for criterion, total_score in criteria_sums.items()
        }
        
        return jsonify({
            'success': True,
            'stats': {
                'total_evaluations': total,
                'average_score': round(average_score, 2),
                'pass_rate': round(pass_rate, 2),
                'criteria_averages': criteria_averages,
                'highest_score': max(scores) if scores else 0,
                'lowest_score': min(scores) if scores else 0
            }
        })
        
    except Exception as e:
        print(f"❌ Error calculating statistics: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'service': 'AI Voice Agent Testing Dashboard API with Auth',
        'timestamp': datetime.now().isoformat()
    })

# ==================== Main ====================

if __name__ == '__main__':
    print("=" * 70)
    print("🚀 Starting Flask Backend with Authentication...")
    print("=" * 70)
    print(f"📊 DynamoDB Tables:")
    print(f"   - {DYNAMODB_TABLE} (evaluations)")
    print(f"   - {USERS_TABLE} (users)")
    print(f"🔑 JWT Expiration: {JWT_EXPIRATION_HOURS} hours")
    print(f"🌐 Server: http://0.0.0.0:5000")
    print(f"📁 Working directory: {os.getcwd()}")
    print("=" * 70)
    print("\n🔐 Authentication Endpoints:")
    print("   POST /api/auth/signup   - Create account")
    print("   POST /api/auth/login    - Login")
    print("   GET  /api/auth/verify   - Verify token")
    print("   POST /api/auth/logout   - Logout")
    print("\n📊 Dashboard Endpoints (Protected):")
    print("   GET  /api/evaluations      - Get all evaluations")
    print("   GET  /api/evaluation/<id>  - Get specific evaluation")
    print("   POST /api/evaluate         - Upload & evaluate CSV")
    print("   GET  /api/stats            - Get statistics")
    print("   GET  /api/health           - Health check")
    print("\n✨ Server ready!\n")
    
    app.run(host='0.0.0.0', port=5000, debug=True)
