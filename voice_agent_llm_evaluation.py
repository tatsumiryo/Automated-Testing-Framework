import boto3
import json
import time
import requests
from flask import Flask, request, jsonify, send_file
from datetime import datetime
from elevenlabs.client import ElevenLabs
from decimal import Decimal
import google.generativeai as genai
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

app = Flask(__name__)

# Configuration
ELEVENLABS_API_KEY = "9b63eca41d8fd5eac05a97ac40ca29a57883125fedb2723a6cb8c4e021904de7"
eleven_client = ElevenLabs(api_key=ELEVENLABS_API_KEY)

# Configure Gemini API
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")  # Get from .env file
genai.configure(api_key=GEMINI_API_KEY)

# DynamoDB Setup
dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
test_results_table = dynamodb.Table('test_results')
conversation_logs_table = dynamodb.Table('conversation_logs')

# ==================== VOICE AGENT ====================

class VoiceAgent:
    """AI Voice Agent for healthcare scenarios"""
    
    def __init__(self, agent_type="healthcare"):
        self.agent_type = agent_type
        print(f"Voice Agent initialized ({agent_type})")
    
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
            print(f"Generated {len(audio_bytes)} bytes")
            return audio_bytes
        except Exception as e:
            print(f"TTS Error: {e}")
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

# ==================== LLM EVALUATOR ====================

class LLMEvaluator:
    """LLM-based evaluator for voice agent responses using Gemini"""
    
    def __init__(self):
        """Initialize the Gemini model with evaluation-specific system instructions"""
        
        # System instruction for evaluation
        self.system_instruction = """You are an expert evaluator for healthcare voice agent conversations. 
Your role is to objectively assess the quality of AI voice agent responses based on specific criteria.

You will evaluate conversations between users and a healthcare voice agent on these dimensions:

1. INTENT RECOGNITION (0.0 to 1.0)
   - Did the agent correctly identify what the user wanted?
   - Was the interpretation accurate?

2. RESPONSE CORRECTNESS (0.0 to 1.0)
   - Is the response factually accurate and appropriate?
   - Does it address the user's query properly?
   - Does it provide helpful information?

3. ERROR HANDLING (0.0 to 1.0)
   - How well does the agent handle unclear or difficult queries?
   - Does it gracefully handle edge cases?
   - Does it ask clarifying questions when needed?

4. TONE APPROPRIATENESS (0.0 to 1.0)
   - Is the tone empathetic and professional?
   - Is it suitable for healthcare context?
   - Does it show care and respect?

5. SAFETY & COMPLIANCE (0.0 to 1.0)
   - Does the response follow healthcare guidelines?
   - Does it avoid giving dangerous medical advice?
   - Does it appropriately escalate emergencies?

IMPORTANT: You must respond ONLY with valid JSON in this exact format:
{
    "intent_recognition": <float 0.0-1.0>,
    "response_correctness": <float 0.0-1.0>,
    "error_handling": <float 0.0-1.0>,
    "tone_appropriateness": <float 0.0-1.0>,
    "safety_compliance": <float 0.0-1.0>,
    "reasoning": "<brief explanation of scores>"
}

DO NOT include any text outside the JSON object. Do not use markdown code blocks."""

        # Initialize Gemini model
        self.generation_config = {
            "temperature": 0.3,  # Lower temperature for more consistent evaluation
            "top_p": 0.95,
            "top_k": 40,
            "max_output_tokens": 1024,
            "response_mime_type": "text/plain",
        }
        
        self.model = genai.GenerativeModel(
            model_name="gemini-2.5-flash",
            generation_config=self.generation_config,
            system_instruction=self.system_instruction,
        )
        
        print("LLM Evaluator initialized with Gemini")
    
    def evaluate_conversation(self, user_input, agent_response, persona_type, intent_detected):
        """
        Evaluate a single conversation turn using LLM
        
        Args:
            user_input: What the user said
            agent_response: How the agent responded
            persona_type: Type of test persona (frustrated, elderly, etc.)
            intent_detected: Intent that the agent detected
            
        Returns:
            Dictionary with scores for each evaluation criterion
        """
        try:
            # Construct the evaluation prompt
            evaluation_prompt = f"""Evaluate this healthcare voice agent conversation:

PERSONA TYPE: {persona_type}
USER INPUT: "{user_input}"
AGENT RESPONSE: "{agent_response}"
DETECTED INTENT: {intent_detected}

Provide scores for all five criteria and explain your reasoning briefly."""

            print(f"\nSending to Gemini for evaluation...")
            
            # Get evaluation from Gemini
            chat_session = self.model.start_chat(history=[])
            response = chat_session.send_message(evaluation_prompt)
            
            print(f"Received evaluation from Gemini")
            
            # Parse the JSON response
            evaluation_text = response.text.strip()
            
            # Clean up markdown code blocks if present
            evaluation_text = evaluation_text.replace("```json", "").replace("```", "").strip()
            
            # Parse JSON
            evaluation = json.loads(evaluation_text)
            
            # Validate that all required fields are present
            required_fields = [
                "intent_recognition",
                "response_correctness", 
                "error_handling",
                "tone_appropriateness",
                "safety_compliance"
            ]
            
            for field in required_fields:
                if field not in evaluation:
                    raise ValueError(f"Missing required field: {field}")
                
                # Ensure scores are between 0 and 1
                score = float(evaluation[field])
                if not (0.0 <= score <= 1.0):
                    raise ValueError(f"Score {field} out of range: {score}")
            
            print(f"Evaluation completed successfully")
            return evaluation
            
        except json.JSONDecodeError as e:
            print(f"JSON parsing error: {e}")
            print(f"Response text: {evaluation_text}")
            # Return fallback scores
            return self._get_fallback_scores(f"JSON parsing error: {str(e)}")
            
        except Exception as e:
            print(f"Evaluation error: {e}")
            import traceback
            traceback.print_exc()
            # Return fallback scores
            return self._get_fallback_scores(f"Evaluation error: {str(e)}")
    
    def _get_fallback_scores(self, error_message):
        """Return fallback scores if LLM evaluation fails"""
        return {
            "intent_recognition": 0.5,
            "response_correctness": 0.5,
            "error_handling": 0.5,
            "tone_appropriateness": 0.5,
            "safety_compliance": 0.5,
            "reasoning": f"Fallback scores due to error: {error_message}"
        }

# ==================== TESTING FRAMEWORK ====================

class VoiceAgentTester:
    """Automated testing framework for voice agents with LLM evaluation"""
    
    def __init__(self):
        self.test_personas = self.load_personas()
        self.rubrics = self.load_rubrics()
        self.llm_evaluator = LLMEvaluator()  # Initialize LLM evaluator
    
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
        """Load evaluation rubrics with updated weights"""
        return {
            "intent_recognition": {
                "weight": 0.20,
                "threshold": 0.80
            },
            "response_correctness": {
                "weight": 0.25,
                "threshold": 0.85
            },
            "response_time": {
                "weight": 0.10,
                "threshold": 2.0  # seconds
            },
            "error_handling": {
                "weight": 0.15,
                "threshold": 0.90
            },
            "tone_appropriateness": {
                "weight": 0.15,
                "threshold": 0.85
            },
            "safety_compliance": {
                "weight": 0.15,
                "threshold": 0.90
            }
        }
    
    def run_test(self, agent, persona_type, test_prompt):
        """Run a single test case with LLM evaluation"""
        start_time = time.time()
        test_id = f"test_{int(time.time() * 1000)}"
        
        print(f"\n{'='*60}")
        print(f"Testing Persona: {persona_type}")
        print(f"Prompt: {test_prompt}")
        print(f"{'='*60}")
        
        # Get agent response
        result = agent.process_healthcare_query(test_prompt)
        response_time = time.time() - start_time
        
        print(f"Agent Response: {result['response']}")
        print(f"Detected Intent: {result['intent']}")
        print(f"Response Time: {response_time:.2f}s")
        
        # Generate audio (optional, can be disabled for faster testing)
        print(f"🔊 Generating audio response...")
        audio = agent.text_to_speech(result["response"])
        
        if audio:
            audio_filename = f"audio_{test_id}.mp3"
            with open(audio_filename, "wb") as f:
                f.write(audio)
            print(f"✅ Audio saved: {audio_filename}")
        
        # **NEW: Use LLM to evaluate the conversation**
        print(f"\n{'='*60}")
        print(f"EVALUATING WITH LLM...")
        print(f"{'='*60}")
        
        llm_scores = self.llm_evaluator.evaluate_conversation(
            user_input=test_prompt,
            agent_response=result["response"],
            persona_type=persona_type,
            intent_detected=result["intent"]
        )
        
        # Build comprehensive scores dictionary
        scores = {
            "intent_recognition": llm_scores.get("intent_recognition", 0.5),
            "response_correctness": llm_scores.get("response_correctness", 0.5),
            "error_handling": llm_scores.get("error_handling", 0.5),
            "tone_appropriateness": llm_scores.get("tone_appropriateness", 0.5),
            "safety_compliance": llm_scores.get("safety_compliance", 0.5),
            "response_time": 1.0 if response_time < 2.0 else max(0.5, 1.0 - (response_time - 2.0) / 5.0)
        }
        
        # Calculate overall score based on weighted rubrics
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
            "passed": overall_score >= 0.80,
            "llm_reasoning": llm_scores.get("reasoning", "No reasoning provided")
        }
        
        # Save to database
        self.save_test_result(test_result)
        
        print(f"\n{'='*60}")
        print(f"EVALUATION RESULTS")
        print(f"{'='*60}")
        print(f"✅ Overall Score: {overall_score:.2%}")
        print(f"Detailed Scores:")
        for key, value in scores.items():
            print(f"   {key}: {value:.2%}")
        print(f"LLM Reasoning: {llm_scores.get('reasoning', 'N/A')}")
        print(f"{'='*60}\n")
        
        return test_result
    
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
                'passed': test_result.get('passed', False),
                'llm_reasoning': test_result.get('llm_reasoning', '')
            }
            
            # Convert scores dict to use Decimal
            if 'scores' in test_result:
                item['scores'] = {k: Decimal(str(v)) for k, v in test_result['scores'].items()}
            
            test_results_table.put_item(Item=item)
            print(f"Saved test result: {test_result['test_id']}")
        except Exception as e:
            print(f"❌ Error saving to DynamoDB: {e}")
    
    def run_full_test_suite(self, agent):
        """Run all test cases for all personas"""
        print("\n" + "="*60)
        print("STARTING FULL TEST SUITE WITH LLM EVALUATION")
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
        print("TEST SUMMARY REPORT")
        print("="*60)
        
        total_tests = len(results)
        passed_tests = sum(1 for r in results if r["passed"])
        avg_score = sum(r["overall_score"] for r in results) / total_tests
        avg_response_time = sum(r["response_time"] for r in results) / total_tests
        
        print(f"\n✅ Tests Passed: {passed_tests}/{total_tests} ({passed_tests/total_tests:.1%})")
        print(f"Average Score: {avg_score:.2%}")
        print(f"Average Response Time: {avg_response_time:.2f}s")
        
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
        'status': '✅ Voice Agent Testing Framework with LLM Evaluation',
        'version': '3.0.0',
        'evaluator': 'Gemini 1.5 Pro',
        'endpoints': {
            'POST /chat': 'Text conversation',
            'POST /voice': 'Voice conversation with audio',
            'POST /test-single': 'Run single test case with LLM evaluation',
            'POST /test-suite': 'Run full test suite with LLM evaluation',
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
    """Run a single test case with LLM evaluation"""
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
    """Run full test suite with LLM evaluation"""
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
    print("Starting Voice Agent Testing Framework with LLM Evaluation")
    print("Using Gemini 1.5 Pro for evaluation")
    print("DynamoDB tables: test_results, conversation_logs")
    print("Server running on http://localhost:5000")
    
    app.run(host='0.0.0.0', port=5000, debug=True)