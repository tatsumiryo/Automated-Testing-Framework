"""
Flask API Extension for Spark Big Data Analytics
Adds endpoints to trigger Spark analysis and retrieve results
"""

from flask import Flask, jsonify, request, send_file
from flask_cors import CORS
import boto3
import json
import subprocess
from datetime import datetime
import os

# Existing Flask app setup (add to your existing app.py)
# This should be integrated with your current Flask application

def add_spark_routes(app):
    """Add Spark analytics routes to existing Flask app"""
    
    # AWS clients
    dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
    s3 = boto3.client('s3', region_name='us-east-1')
    emr = boto3.client('emr', region_name='us-east-1')
    
    RESULTS_TABLE = "conversation_analytics_results"
    EMR_CLUSTER_ID = os.environ.get('EMR_CLUSTER_ID', None)
    S3_BUCKET = os.environ.get('S3_BUCKET', 'your-analytics-bucket')
    
    @app.route('/api/analytics/trigger', methods=['POST'])
    def trigger_spark_analysis():
        """Trigger Spark big data analysis job on EMR"""
        try:
            # Use existing Spark script in S3 (no upload needed)
            s3_script_key = 'spark-scripts/spark_sentiment_analysis.py'
            
            print(f"✅ Using Spark script: s3://{S3_BUCKET}/{s3_script_key}")
            
            # Submit Spark job to EMR
            if not EMR_CLUSTER_ID:
                return jsonify({
                    'success': False,
                    'error': 'EMR cluster not configured'
                }), 500
            
            response = emr.add_job_flow_steps(
                JobFlowId=EMR_CLUSTER_ID,
                Steps=[
                    {
                        'Name': 'Healthcare Conversation Sentiment Analysis',
                        'ActionOnFailure': 'CONTINUE',
                        'HadoopJarStep': {
                            'Jar': 'command-runner.jar',
                            'Args': [
                                'spark-submit',
                                '--deploy-mode', 'cluster',
                                '--master', 'yarn',
                                f's3://{S3_BUCKET}/{s3_script_key}'
                            ]
                        }
                    }
                ]
            )
            
            step_id = response['StepIds'][0]
            
            return jsonify({
                'success': True,
                'message': 'Spark analysis job submitted',
                'step_id': step_id,
                'cluster_id': EMR_CLUSTER_ID
            })
            
        except Exception as e:
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500
    
    @app.route('/api/analytics/status/<step_id>', methods=['GET'])
    def get_analysis_status(step_id):
        """Get status of Spark analysis job"""
        try:
            if not EMR_CLUSTER_ID:
                return jsonify({
                    'success': False,
                    'error': 'EMR cluster not configured'
                }), 500
            
            response = emr.describe_step(
                ClusterId=EMR_CLUSTER_ID,
                StepId=step_id
            )
            
            step = response['Step']
            
            return jsonify({
                'success': True,
                'status': step['Status']['State'],
                'timeline': step['Status']['Timeline'],
                'name': step['Name']
            })
            
        except Exception as e:
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500
    
    @app.route('/api/analytics/results', methods=['GET'])
    def get_latest_results():
        """Get latest analytics results from DynamoDB"""
        try:
            table = dynamodb.Table(RESULTS_TABLE)
            
            # Scan and get most recent analysis
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
            table = dynamodb.Table('test_results')
            
            response = table.scan()
            items = response.get('Items', [])
            
            # Filter conversations that have sentiment data
            conversations_with_sentiment = [
                {
                    'conversation_id': item.get('conversation_id'),
                    'title': item.get('conversation_title', 'Untitled'),
                    'medical_sentiment': item.get('medical_sentiment', 0),
                    'urgency_level': item.get('urgency_level', 0),
                    'dominant_emotion': item.get('dominant_emotion', 'neutral'),
                    'sentiment_category': item.get('sentiment_category', 'Neutral'),
                    'urgency_category': item.get('urgency_category', 'Low'),
                    'complexity_score': item.get('complexity_score', 0),
                    'overall_score': item.get('overall_evaluation_score', 0)
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
            
            # Get analysis results
            table = dynamodb.Table(RESULTS_TABLE)
            response = table.get_item(Key={'analysis_id': analysis_id})
            
            if 'Item' not in response:
                return jsonify({
                    'success': False,
                    'message': 'Analysis not found'
                }), 404
            
            # Generate PDF (you'll need to implement this)
            # For now, return JSON
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
    
    print("Spark analytics routes added to Flask app")

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)