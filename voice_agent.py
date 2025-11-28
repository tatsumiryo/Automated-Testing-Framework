import boto3
import json
import time
import requests
from flask import Flask, request, jsonify
from datetime import datetime
from elevenlabs.client import ElevenLabs
from decimal import Decimal
from flask import Flask, request, jsonify, send_file

app = Flask(__name__)

# Configuration
ELEVENLABS_API_KEY = "9b63eca41d8fd5eac05a97ac40ca29a57883125fedb2723a6cb8c4e021904de7"
eleven_client = ElevenLabs(api_key=ELEVENLABS_API_KEY)

# DynamoDB Setup
dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
test_results_table = dynamodb.Table('test_results')
conversation_logs_table = dynamodb.Table('conversation_logs')

# ==================== VOICE AGENT ====================

class VoiceAgent:
    """AI Voice Agent for healthcare scenarios"""
    
    def __init__(self, agent_type="healthcare"):
        self.agent_type = agent_type
        print(f"🤖 Voice Agent initialized ({agent_type})")
    
    def text_to_speech(self, text, voice="Rachel"):
        """Convert text to speech"""
        try:
            print(f"🔊 Generating speech for: {text[:50]}...")
            voice_id = "21m00Tcm4TlvDq8ikWAM"  # Rachel
            audio = eleven_client.text_to_speech.convert(
                text=text,
                voice_id=voice_id
            )
            audio_bytes = b''.join(audio)
            print(f"✅ Generated {len(audio_bytes)} bytes")
            return audio_bytes
        except Exception as e:
            print(f"❌ TTS Error: {e}")
            import traceback
            traceback.print_exc()
            return None
        
    def process_healthcare_query(self, user_input):
        """Process healthcare-related queries"""
        user_lower = user_input.lower()
        
        # Appointment booking
        if any(word in user_lower for word in ["book", "appointment", "schedule"]):
            return {
                "response": "I'd be happy to help you book an appointment. Could you please tell me your preferred date and what type of visit you need?",
                "intent": "appointment_booking",
                "confidence": 0.95
            }
        
        # Medication queries
        elif any(word in user_lower for word in ["medicine", "medication", "headache", "fever"]):
            return {
                "response": "For over-the-counter medication, I recommend consulting with a pharmacist. If your symptoms persist or worsen, please schedule an appointment with a doctor. Would you like me to book an appointment for you?",
                "intent": "medication_query",
                "confidence": 0.90
            }
        
        # Emergency/Accident
        elif any(word in user_lower for word in ["accident", "emergency", "scalded", "sprained"]):
            return {
                "response": "For immediate medical concerns, please call emergency services or visit the nearest hospital. For minor injuries, I can guide you through basic first aid. What kind of injury occurred?",
                "intent": "emergency_query",
                "confidence": 0.98
            }
        
        # Appointment reminders (outbound)
        elif "confirm" in user_lower or "reminder" in user_lower:
            return {
                "response": "Hello! This is a reminder for your appointment. Can you confirm you'll be attending?",
                "intent": "appointment_reminder",
                "confidence": 0.92
            }
        
        # Default response
        else:
            return {
                "response": f"I understand you said: '{user_input}'. I'm here to help with appointments, health queries, and medical guidance. How can I assist you?",
                "intent": "general_query",
                "confidence": 0.70
            }

# ==================== TESTING FRAMEWORK ====================

class VoiceAgentTester:
    """Automated testing framework for voice agents"""
    
    def __init__(self):
        self.test_personas = self.load_personas()
        self.rubrics = self.load_rubrics()
    
    def load_personas(self):
        """Load test personas"""
        return {
            "frustrated": {
                "name": "Frustrated Customer",
                "characteristics": ["negative_tone", "interruptions", "urgent"],
                "test_prompts": [
                    "I've been waiting forever! I need to see a doctor NOW!",
                    "This is ridiculous, why is this taking so long?!"
                ]
            },
            "non_native": {
                "name": "Non-Native Speaker",
                "characteristics": ["accented", "mispronunciation", "unusual_grammar"],
                "test_prompts": [
                    "I am needing appointment with doctor for the headache",
                    "My head is pain very much, what medicine I take?"
                ]
            },
            "fast_speaker": {
                "name": "Fast Speaker",
                "characteristics": ["rapid_speech", "high_information_density"],
                "test_prompts": [
                    "HiIneedanappointmentfordoctorvisittomorrowmorningpreferablyaround9amforcheckup"
                ]
            },
            "elderly": {
                "name": "Elderly/Slow Speaker",
                "characteristics": ["slow_speech", "pauses", "repetition"],
                "test_prompts": [
                    "Hello... I need... um... I need to book... an appointment... please",
                    "Can you... help me... I forgot... what was I saying?"
                ]
            },
            "vague": {
                "name": "Vague User",
                "characteristics": ["incomplete_info", "ambiguous"],
                "test_prompts": [
                    "I need help with something",
                    "Can you help me with that thing we discussed?"
                ]
            }
        }
    
    def load_rubrics(self):
        """Load evaluation rubrics"""
        return {
            "intent_recognition": {
                "weight": 0.25,
                "threshold": 0.80
            },
            "response_correctness": {
                "weight": 0.25,
                "threshold": 0.85
            },
            "response_time": {
                "weight": 0.15,
                "threshold": 2.0  # seconds
            },
            "error_handling": {
                "weight": 0.15,
                "threshold": 0.90
            },
            "tone_appropriateness": {
                "weight": 0.20,
                "threshold": 0.85
            }
        }
    
    def run_test(self, agent, persona_type, test_prompt):
        """Run a single test case"""
        start_time = time.time()
        test_id = f"test_{int(time.time() * 1000)}"
        
        print(f"\n🧪 Testing Persona: {persona_type}")
        print(f"📝 Prompt: {test_prompt}")
        
        # Get agent response
        result = agent.process_healthcare_query(test_prompt)
        response_time = time.time() - start_time
        print(f"🔊 Generating audio response...")
        audio = agent.text_to_speech(result["response"])

        if audio:
            audio_filename = f"audio_{test_id}.mp3"
            with open(audio_filename, "wb") as f:
                f.write(audio)
            print(f"✅ Audio saved: {audio_filename}")
        else:
            print(f"❌ Audio generation failed")
        
        # Evaluate based on rubrics
        scores = self.evaluate_response(result, response_time, persona_type)
        
        # Calculate overall score
        overall_score = sum(
            scores[key] * self.rubrics[key]["weight"] 
            for key in self.rubrics.keys()
        )
        
        # Store results in DynamoDB
        test_result = {
            "test_id": test_id,
            "timestamp": datetime.now().isoformat(),
            "persona_type": persona_type,
            "test_prompt": test_prompt,
            "agent_response": result["response"],
            "intent_detected": result["intent"],
            "confidence": result["confidence"],
            "response_time": response_time,
            "scores": scores,
            "overall_score": overall_score,
            "passed": overall_score >= 0.80
        }
        
        # Save to database
        self.save_test_result(test_result)
        
        print(f"✅ Overall Score: {overall_score:.2%}")
        print(f"📊 Detailed Scores: {scores}")
        
        return test_result
    
    def evaluate_response(self, result, response_time, persona_type):
        """Evaluate response against rubrics"""
        scores = {}
        
        # Intent Recognition (based on confidence)
        scores["intent_recognition"] = min(result["confidence"], 1.0)
        
        # Response Correctness (check if response is appropriate)
        has_helpful_content = len(result["response"]) > 20
        has_question = "?" in result["response"]
        scores["response_correctness"] = 0.9 if has_helpful_content else 0.6
        
        # Response Time
        scores["response_time"] = 1.0 if response_time < 2.0 else max(0.5, 1.0 - (response_time - 2.0) / 5.0)
        
        # Error Handling (check for graceful responses)
        has_fallback = "understand" in result["response"].lower() or "help" in result["response"].lower()
        scores["error_handling"] = 0.9 if has_fallback else 0.7
        
        # Tone Appropriateness (check for empathy and professionalism)
        empathetic_words = ["happy", "understand", "help", "please", "thank you"]
        tone_score = sum(1 for word in empathetic_words if word in result["response"].lower()) / len(empathetic_words)
        scores["tone_appropriateness"] = min(tone_score + 0.5, 1.0)
        
        return scores
    
    def save_test_result(self, test_result):
        """Save test result to DynamoDB"""
        try:
            # Convert floats to Decimal for DynamoDB
            item = {
                'test_id': test_result['test_id'],
                'timestamp': test_result['timestamp'],
                'persona_type': test_result.get('persona_type', ''),
                'test_prompt': test_result.get('test_prompt', ''),
                'agent_response': test_result.get('agent_response', ''),
                'intent_detected': test_result.get('intent_detected', ''),
                'confidence': Decimal(str(test_result.get('confidence', 0))),
                'response_time': Decimal(str(test_result.get('response_time', 0))),
                'overall_score': Decimal(str(test_result.get('overall_score', 0))),
                'passed': test_result.get('passed', False)
            }
            
            # Convert scores dict to use Decimal
            if 'scores' in test_result:
                item['scores'] = {k: Decimal(str(v)) for k, v in test_result['scores'].items()}
            
            test_results_table.put_item(Item=item)
            print(f"💾 Saved test result: {test_result['test_id']}")
        except Exception as e:
            print(f"❌ Error saving to DynamoDB: {e}")
    
    def run_full_test_suite(self, agent):
        """Run all test cases for all personas"""
        print("\n" + "="*60)
        print("🚀 STARTING FULL TEST SUITE")
        print("="*60)
        
        all_results = []
        
        for persona_type, persona_data in self.test_personas.items():
            print(f"\n{'='*60}")
            print(f"Testing Persona: {persona_data['name']}")
            print(f"{'='*60}")
            
            for prompt in persona_data["test_prompts"]:
                result = self.run_test(agent, persona_type, prompt)
                all_results.append(result)
                time.sleep(1)  # Avoid rate limiting
        
        # Generate summary
        self.generate_test_summary(all_results)
        
        return all_results
    
    def generate_test_summary(self, results):
        """Generate test summary report"""
        print("\n" + "="*60)
        print("📊 TEST SUMMARY REPORT")
        print("="*60)
        
        total_tests = len(results)
        passed_tests = sum(1 for r in results if r["passed"])
        avg_score = sum(r["overall_score"] for r in results) / total_tests
        avg_response_time = sum(r["response_time"] for r in results) / total_tests
        
        print(f"\n✅ Tests Passed: {passed_tests}/{total_tests} ({passed_tests/total_tests:.1%})")
        print(f"📈 Average Score: {avg_score:.2%}")
        print(f"⏱️  Average Response Time: {avg_response_time:.2f}s")
        
        print("\n📋 Breakdown by Persona:")
        persona_scores = {}
        for result in results:
            persona = result["persona_type"]
            if persona not in persona_scores:
                persona_scores[persona] = []
            persona_scores[persona].append(result["overall_score"])
        
        for persona, scores in persona_scores.items():
            avg = sum(scores) / len(scores)
            print(f"  {persona}: {avg:.2%}")

# ==================== FLASK API ROUTES ====================

voice_agent = VoiceAgent()
tester = VoiceAgentTester()

@app.route('/', methods=['GET'])
def home():
    return jsonify({
        'status': '✅ Voice Agent Testing Framework',
        'version': '2.0.0',
        'endpoints': {
            'POST /chat': 'Text conversation',
            'POST /voice': 'Voice conversation with audio',
            'POST /test-single': 'Run single test case',
            'POST /test-suite': 'Run full test suite',
            'GET /results': 'Get all test results',
            'GET /results/<test_id>': 'Get specific test result'
        }
    })

@app.route('/chat', methods=['POST'])
def chat():
    """Text conversation endpoint"""
    try:
        data = request.get_json()
        user_text = data.get('text', '')
        
        if not user_text:
            return jsonify({'error': 'No text provided'}), 400
        
        result = voice_agent.process_healthcare_query(user_text)
        
        log_entry = {
            "test_id": f"log_{int(time.time() * 1000)}",
            "turn_number": 1,
            "timestamp": datetime.now().isoformat(),
            "user_input": user_text,
            "agent_response": result["response"],
            "intent": result["intent"],
            "confidence": Decimal(str(result["confidence"]))
        }
        
        conversation_logs_table.put_item(Item=log_entry)
        
        return jsonify(result)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/voice', methods=['POST'])
def voice_chat():
    """Voice conversation with audio output"""
    try:
        data = request.get_json()
        user_text = data.get('text', '')
        voice = data.get('voice', 'Rachel')
        
        if not user_text:
            return jsonify({'error': 'No text provided'}), 400
        
        # Get response
        result = voice_agent.process_healthcare_query(user_text)
        
        # Generate audio
        audio = voice_agent.text_to_speech(result["response"], voice)
        
        if audio:
            filename = f"response_{int(time.time())}.mp3"
            with open(filename, "wb") as f:
                f.write(audio)
            
            return jsonify({
                **result,
                'audio_generated': True,
                'audio_size': len(audio),
                'filename': filename
            })
        else:
            return jsonify({**result, 'audio_generated': False}), 500
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/test-single', methods=['POST'])
def test_single():
    """Run a single test case"""
    try:
        data = request.get_json()
        persona_type = data.get('persona_type', 'frustrated')
        test_prompt = data.get('test_prompt')
        
        if not test_prompt:
            # Use default prompt for persona
            test_prompt = tester.test_personas[persona_type]["test_prompts"][0]
        
        result = tester.run_test(voice_agent, persona_type, test_prompt)
        
        return jsonify(result)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/test-suite', methods=['POST'])
def test_suite():
    """Run full test suite"""
    try:
        results = tester.run_full_test_suite(voice_agent)
        
        return jsonify({
            'total_tests': len(results),
            'passed': sum(1 for r in results if r["passed"]),
            'average_score': sum(r["overall_score"] for r in results) / len(results),
            'results': results
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/results', methods=['GET'])
def get_results():
    """Get all test results from DynamoDB"""
    try:
        response = test_results_table.scan()
        return jsonify({
            'count': len(response['Items']),
            'results': response['Items']
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/results/<test_id>', methods=['GET'])
def get_result(test_id):
    """Get specific test result"""
    try:
        response = test_results_table.get_item(Key={'test_id': test_id})
        
        if 'Item' in response:
            return jsonify(response['Item'])
        else:
            return jsonify({'error': 'Test not found'}), 404
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/dashboard', methods=['GET'])
def dashboard():
    """Serve the analytics dashboard"""
    return send_file('dashboard.html')

if __name__ == '__main__':
    print("🚀 Starting Voice Agent Testing Framework")
    print("📊 DynamoDB tables: test_results, conversation_logs")
    print("🌐 Server running on http://localhost:5000")
    
    app.run(host='0.0.0.0', port=5000, debug=True)