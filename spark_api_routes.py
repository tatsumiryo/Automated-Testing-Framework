"""
Flask API Extension for AWS-based Analytics with Mock Data
Uses DynamoDB for storage, processes mock data locally
"""

from flask import Flask, jsonify, request
from flask_cors import CORS
import boto3
from boto3.dynamodb.conditions import Key
import json
from datetime import datetime
from textblob import TextBlob
import os

def add_spark_routes(app):
    """Add AWS-based analytics routes to existing Flask app"""
    
    # AWS clients
    dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
    
    RESULTS_TABLE = "conversation_analytics_results"
    CONVERSATIONS_TABLE = "test_results"
    MOCK_DATA_PATH = 'conversations_mock_data2.json'
    
    def analyze_sentiment(text):
        """Analyze sentiment using TextBlob"""
        blob = TextBlob(text)
        return blob.sentiment.polarity
    
    def detect_urgency_keywords(text):
        """Detect urgency based on keywords"""
        urgent_keywords = [
            'emergency', 'urgent', 'severe', 'critical', 'immediately',
            'chest pain', 'can\'t breathe', 'bleeding', 'unconscious',
            'allergic reaction', 'overdose', 'stroke', 'heart attack'
        ]
        text_lower = text.lower()
        urgency_score = sum(1 for keyword in urgent_keywords if keyword in text_lower)
        return min(urgency_score / 3, 1.0)
    
    def detect_emotion(text, sentiment):
        """Detect dominant emotion"""
        text_lower = text.lower()
        
        if any(word in text_lower for word in ['scared', 'worried', 'anxious', 'afraid', 'nervous']):
            return 'anxious'
        if any(word in text_lower for word in ['frustrated', 'angry', 'upset', 'annoyed']):
            return 'frustrated'
        if any(word in text_lower for word in ['grateful', 'thank', 'appreciate', 'wonderful']):
            return 'grateful'
        if any(word in text_lower for word in ['confused', 'don\'t understand', 'unclear']):
            return 'confused'
        if any(word in text_lower for word in ['pain', 'hurt', 'ache']):
            return 'distressed'
        
        if sentiment > 0.3:
            return 'positive'
        elif sentiment < -0.3:
            return 'negative'
        else:
            return 'neutral'
    
    def calculate_complexity(text):
        """Calculate conversation complexity"""
        words = len(text.split())
        sentences = text.count('.') + text.count('!') + text.count('?')
        medical_terms = ['medication', 'diagnosis', 'treatment', 'symptom', 'procedure', 
                        'lab', 'test', 'specialist', 'therapy', 'prescription']
        medical_count = sum(1 for term in medical_terms if term in text.lower())
        
        complexity = min((words / 100 + sentences / 10 + medical_count / 5) / 3, 1.0)
        return complexity
    
    def categorize_sentiment(score):
        """Categorize sentiment score"""
        if score > 0.3:
            return 'Positive'
        elif score < -0.3:
            return 'Negative'
        else:
            return 'Neutral'
    
    def categorize_urgency(score):
        """Categorize urgency score"""
        if score > 0.7:
            return 'Critical'
        elif score > 0.4:
            return 'High'
        elif score > 0.2:
            return 'Medium'
        else:
            return 'Low'
    
    def generate_insights(conversations_analyzed):
        """Generate insights from analyzed conversations"""
        insights = []
        
        sentiment_counts = {'Positive': 0, 'Negative': 0, 'Neutral': 0}
        urgency_counts = {'Critical': 0, 'High': 0, 'Medium': 0, 'Low': 0}
        
        for conv in conversations_analyzed:
            sentiment_counts[conv['sentiment_category']] += 1
            urgency_counts[conv['urgency_category']] += 1
        
        total = len(conversations_analyzed)
        
        negative_pct = (sentiment_counts['Negative'] / total) * 100
        if negative_pct > 30:
            insights.append({
                'category': 'sentiment',
                'priority': 'high',
                'message': f'{negative_pct:.1f}% of conversations show negative sentiment. Consider staff training on empathetic communication.'
            })
        
        critical_urgent = urgency_counts['Critical'] + urgency_counts['High']
        urgent_pct = (critical_urgent / total) * 100
        if urgent_pct > 20:
            insights.append({
                'category': 'urgency',
                'priority': 'critical',
                'message': f'{urgent_pct:.1f}% of conversations are urgent/critical. Review triage protocols.'
            })
        
        positive_pct = (sentiment_counts['Positive'] / total) * 100
        if positive_pct > 50:
            insights.append({
                'category': 'quality',
                'priority': 'low',
                'message': f'{positive_pct:.1f}% of patients express positive sentiment. Patient satisfaction is strong.'
            })
        
        return insights
    
    @app.route('/api/analytics/trigger', methods=['POST'])
    def trigger_analysis():
        """Process mock data and store results in DynamoDB"""
        try:
            # Load mock data
            if not os.path.exists(MOCK_DATA_PATH):
                return jsonify({
                    'success': False,
                    'error': f'Mock data file not found: {MOCK_DATA_PATH}'
                }), 404
            
            with open(MOCK_DATA_PATH, 'r') as f:
                conversations = json.load(f)
            
            print(f"Processing {len(conversations)} conversations...")
            
            conversations_table = dynamodb.Table(CONVERSATIONS_TABLE)
            results_table = dynamodb.Table(RESULTS_TABLE)
            
            # Analyze each conversation and store in DynamoDB
            analyzed_conversations = []
            for conv in conversations:
                text = conv['conversation_text']
                
                sentiment_score = analyze_sentiment(text)
                urgency_score = detect_urgency_keywords(text)
                emotion = detect_emotion(text, sentiment_score)
                complexity = calculate_complexity(text)
                
                overall_score = int((
                    (sentiment_score + 1) / 2 * 30 +
                    (1 - urgency_score) * 30 +
                    (1 - complexity) * 20 +
                    20
                ))
                
                analyzed_conv = {
                    'conversation_id': conv['conversation_id'],
                    'conversation_title': f"{conv['appointment_type'].replace('_', ' ').title()} - Age {conv['patient_age']}",
                    'medical_sentiment': round(sentiment_score, 4),
                    'urgency_level': round(urgency_score, 4),
                    'dominant_emotion': emotion,
                    'complexity_score': round(complexity, 4),
                    'sentiment_category': categorize_sentiment(sentiment_score),
                    'urgency_category': categorize_urgency(urgency_score),
                    'overall_evaluation_score': overall_score,
                    'timestamp': conv['timestamp'],
                    'patient_age': conv['patient_age'],
                    'appointment_type': conv['appointment_type']
                }
                
                analyzed_conversations.append(analyzed_conv)
                
                # Store in DynamoDB conversations table
                try:
                    conversations_table.put_item(Item=analyzed_conv)
                except Exception as e:
                    print(f"Warning: Could not store conversation {conv['conversation_id']}: {e}")
            
            # Calculate aggregate metrics
            total_convs = len(analyzed_conversations)
            avg_sentiment = sum(c['medical_sentiment'] for c in analyzed_conversations) / total_convs
            avg_urgency = sum(c['urgency_level'] for c in analyzed_conversations) / total_convs
            avg_complexity = sum(c['complexity_score'] for c in analyzed_conversations) / total_convs
            
            # Count distributions
            sentiment_dist = {}
            emotion_dist = {}
            urgency_dist = {}
            
            for conv in analyzed_conversations:
                sent_cat = conv['sentiment_category']
                sentiment_dist[sent_cat] = sentiment_dist.get(sent_cat, 0) + 1
                
                emotion = conv['dominant_emotion']
                emotion_dist[emotion] = emotion_dist.get(emotion, 0) + 1
                
                urg_cat = conv['urgency_category']
                urgency_dist[urg_cat] = urgency_dist.get(urg_cat, 0) + 1
            
            # Generate insights
            insights = generate_insights(analyzed_conversations)
            
            # Create results
            analysis_id = f"analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            timestamp = datetime.now().isoformat()
            
            metrics = {
                'overall_stats': {
                    'total_conversations': total_convs,
                    'avg_sentiment': round(avg_sentiment, 4),
                    'avg_urgency': round(avg_urgency, 4),
                    'avg_complexity': round(avg_complexity, 4)
                },
                'sentiment_distribution': sentiment_dist,
                'emotion_distribution': emotion_dist,
                'urgency_distribution': urgency_dist
            }
            
            # Store results in DynamoDB
            result_item = {
                'analysis_id': analysis_id,
                'timestamp': timestamp,
                'metrics': json.dumps(metrics),
                'insights': json.dumps(insights),
                'total_conversations_analyzed': total_convs
            }
            
            try:
                results_table.put_item(Item=result_item)
                print(f"✅ Results stored in DynamoDB: {analysis_id}")
            except Exception as e:
                print(f"Warning: Could not store results in DynamoDB: {e}")
            
            return jsonify({
                'success': True,
                'message': 'Analysis completed and stored in DynamoDB',
                'analysis_id': analysis_id,
                'mode': 'aws_mock_data'
            })
            
        except Exception as e:
            import traceback
            traceback.print_exc()
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500
    
    @app.route('/api/analytics/status/<step_id>', methods=['GET'])
    def get_analysis_status(step_id):
        """Get status - for mock data processing, always return completed"""
        return jsonify({
            'success': True,
            'status': 'COMPLETED',
            'timeline': {
                'CreationDateTime': datetime.now().isoformat()
            },
            'name': 'AWS Mock Data Analysis'
        })
    
    @app.route('/api/analytics/results', methods=['GET'])
    def get_latest_results():
        """Get latest analytics results from DynamoDB"""
        try:
            table = dynamodb.Table(RESULTS_TABLE)
            
            response = table.scan()
            items = response.get('Items', [])
            
            if not items:
                return jsonify({
                    'success': False,
                    'message': 'No analysis results found'
                }), 404
            
            # Sort by timestamp and get latest
            items.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
            latest = items[0]
            
            # Parse JSON strings
            metrics = json.loads(latest.get('metrics', '{}'))
            insights = json.loads(latest.get('insights', '[]'))
            
            return jsonify({
                'success': True,
                'analysis_id': latest['analysis_id'],
                'timestamp': latest['timestamp'],
                'metrics': metrics,
                'insights': insights,
                'total_conversations': latest.get('total_conversations_analyzed', 0)
            })
            
        except Exception as e:
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500
    
    @app.route('/api/analytics/results/<analysis_id>', methods=['GET'])
    def get_specific_results(analysis_id):
        """Get specific analysis results by ID"""
        try:
            table = dynamodb.Table(RESULTS_TABLE)
            
            response = table.get_item(Key={'analysis_id': analysis_id})
            
            if 'Item' not in response:
                return jsonify({
                    'success': False,
                    'message': 'Analysis not found'
                }), 404
            
            item = response['Item']
            
            # Parse JSON strings
            metrics = json.loads(item.get('metrics', '{}'))
            insights = json.loads(item.get('insights', '[]'))
            
            return jsonify({
                'success': True,
                'analysis_id': item['analysis_id'],
                'timestamp': item['timestamp'],
                'metrics': metrics,
                'insights': insights,
                'total_conversations': item.get('total_conversations_analyzed', 0)
            })
            
        except Exception as e:
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500
    
    @app.route('/api/analytics/history', methods=['GET'])
    def get_analysis_history():
        """Get historical analysis results"""
        try:
            table = dynamodb.Table(RESULTS_TABLE)
            
            response = table.scan()
            items = response.get('Items', [])
            
            # Sort by timestamp
            items.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
            
            # Return summary of each analysis
            history = []
            for item in items:
                history.append({
                    'analysis_id': item['analysis_id'],
                    'timestamp': item['timestamp'],
                    'total_conversations': item.get('total_conversations_analyzed', 0)
                })
            
            return jsonify({
                'success': True,
                'history': history,
                'count': len(history)
            })
            
        except Exception as e:
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500
    
    @app.route('/api/analytics/conversations/sentiment', methods=['GET'])
    def get_conversations_with_sentiment():
        """Get all conversations with sentiment analysis data"""
        try:
            table = dynamodb.Table(CONVERSATIONS_TABLE)
            
            response = table.scan()
            items = response.get('Items', [])
            
            # Filter conversations that have sentiment data
            conversations_with_sentiment = [
                {
                    'conversation_id': item.get('conversation_id'),
                    'title': item.get('conversation_title', 'Untitled'),
                    'medical_sentiment': float(item.get('medical_sentiment', 0)),
                    'urgency_level': float(item.get('urgency_level', 0)),
                    'dominant_emotion': item.get('dominant_emotion', 'neutral'),
                    'sentiment_category': item.get('sentiment_category', 'Neutral'),
                    'urgency_category': item.get('urgency_category', 'Low'),
                    'complexity_score': float(item.get('complexity_score', 0)),
                    'overall_score': int(item.get('overall_evaluation_score', 0))
                }
                for item in items
                if 'medical_sentiment' in item
            ]
            
            return jsonify({
                'success': True,
                'conversations': conversations_with_sentiment,
                'count': len(conversations_with_sentiment)
            })
            
        except Exception as e:
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500
    
    @app.route('/api/analytics/export/pdf', methods=['POST'])
    def export_analytics_pdf():
        """Export analytics results as PDF report"""
        try:
            data = request.json
            analysis_id = data.get('analysis_id')
            
            if not analysis_id:
                return jsonify({
                    'success': False,
                    'error': 'Analysis ID required'
                }), 400
            
            table = dynamodb.Table(RESULTS_TABLE)
            response = table.get_item(Key={'analysis_id': analysis_id})
            
            if 'Item' not in response:
                return jsonify({
                    'success': False,
                    'message': 'Analysis not found'
                }), 404
            
            return jsonify({
                'success': True,
                'message': 'PDF export feature coming soon',
                'download_url': f'/api/analytics/export/{analysis_id}.pdf'
            })
            
        except Exception as e:
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500
    
    print("✅ AWS analytics routes (with mock data) added to Flask app")

if __name__ == '__main__':
    from flask import Flask
    app = Flask(__name__)
    CORS(app)
    add_spark_routes(app)
    app.run(host='0.0.0.0', port=5000, debug=True)