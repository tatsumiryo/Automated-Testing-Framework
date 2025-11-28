"""
Advanced Healthcare Conversation Analytics with PySpark
Uses multiple sentiment analysis techniques and statistical models
"""

from pyspark.sql import SparkSession
from pyspark.sql.functions import (
    col, udf, explode, split, lower, regexp_replace, 
    count, avg, sum as _sum, max as _max, min as _min,
    when, window, to_timestamp, struct, collect_list,
    monotonically_increasing_id, row_number, rank, dense_rank
)
from pyspark.sql.types import (
    StringType, FloatType, ArrayType, StructType, 
    StructField, IntegerType, DoubleType
)
from pyspark.sql.window import Window
from pyspark.ml.feature import (
    Tokenizer, StopWordsRemover, HashingTF, IDF, 
    Word2Vec, CountVectorizer
)
from pyspark.ml.clustering import LDA
from pyspark.ml import Pipeline

import boto3
import json
from datetime import datetime
import re
from typing import List, Dict, Tuple
# import numpy as np


class HealthcareConversationAnalyzer:
    """
    Advanced Big Data Analytics for Healthcare Conversations
    Implements multiple NLP techniques for comprehensive analysis
    """
    
    def __init__(self, dynamodb_table: str = "test_results"):
        """Initialize Spark session and AWS clients"""
        self.spark = SparkSession.builder \
            .appName("HealthcareConversationAnalytics") \
            .config("spark.sql.adaptive.enabled", "true") \
            .config("spark.sql.adaptive.coalescePartitions.enabled", "true") \
            .config("spark.dynamodb.region", "us-east-1") \
            .getOrCreate()
        
        self.dynamodb_table = dynamodb_table
        self.dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
        self.table = self.dynamodb.Table(dynamodb_table)
        
        # Medical domain-specific sentiment lexicon
        self.medical_positive_terms = [
            'better', 'improved', 'recovering', 'helping', 'comfortable',
            'relief', 'stable', 'progress', 'healing', 'effective',
            'grateful', 'thankful', 'appreciate', 'satisfied', 'resolved'
        ]
        
        self.medical_negative_terms = [
            'pain', 'worse', 'suffering', 'discomfort', 'anxious',
            'worried', 'concerned', 'frustrated', 'confused', 'upset',
            'afraid', 'scared', 'angry', 'disappointed', 'distressed'
        ]
        
        self.urgency_keywords = [
            'emergency', 'urgent', 'immediate', 'critical', 'severe',
            'life-threatening', 'cannot breathe', 'chest pain', 'bleeding',
            'unconscious', 'suicide', 'overdose'
        ]
        
        # Register UDFs
        self._register_udfs()
    
    def _register_udfs(self):
        """Register User Defined Functions for sentiment analysis"""
        
        # Medical-specific sentiment scoring
        @udf(FloatType())
        def medical_sentiment_score(text):
            if not text:
                return 0.0
            
            text_lower = text.lower()
            positive_count = sum(1 for term in self.medical_positive_terms if term in text_lower)
            negative_count = sum(1 for term in self.medical_negative_terms if term in text_lower)
            
            total_words = len(text.split())
            if total_words == 0:
                return 0.0
            
            # Normalized sentiment score between -1 and 1
            score = (positive_count - negative_count) / max(total_words, 1)
            return float(max(-1.0, min(score, 1.0))) 
        
        # Urgency detection
        @udf(FloatType())
        def urgency_score(text):
            if not text:
                return 0.0
            
            text_lower = text.lower()
            urgency_matches = sum(1 for keyword in self.urgency_keywords if keyword in text_lower)
            
            # Weight by exclamation marks and capital letters
            exclamation_count = text.count('!')
            caps_ratio = sum(1 for c in text if c.isupper()) / max(len(text), 1)
            
            score = (urgency_matches * 0.6) + (exclamation_count * 0.2) + (caps_ratio * 0.2)
            return float(min(score, 1.0))
        
        # Emotion detection
        @udf(StringType())
        def detect_emotion(text):
            if not text:
                return "neutral"
            
            text_lower = text.lower()
            
            # Emotion patterns
            if any(word in text_lower for word in ['anxious', 'worried', 'nervous', 'scared']):
                return "anxiety"
            elif any(word in text_lower for word in ['angry', 'frustrated', 'annoyed']):
                return "anger"
            elif any(word in text_lower for word in ['sad', 'depressed', 'crying', 'grief']):
                return "sadness"
            elif any(word in text_lower for word in ['happy', 'glad', 'better', 'relieved']):
                return "positive"
            elif any(word in text_lower for word in ['confused', 'unsure', 'don\'t understand']):
                return "confusion"
            else:
                return "neutral"
        
        # Question identification
        @udf(IntegerType())
        def count_questions(text):
            if not text:
                return 0
            return text.count('?')
        
        # Conversation complexity
        @udf(FloatType())
        def complexity_score(text):
            if not text:
                return 0.0
            
            words = text.split()
            avg_word_length = sum([len(word) for word in words]) / len(words) if words else 0
            sentence_count = max(len(re.split(r'[.!?]', text)), 1)
            words_per_sentence = len(words) / sentence_count
            
            # Normalized complexity (0-1)
            complexity = (avg_word_length / 10 + words_per_sentence / 20) / 2
            return float(min(complexity, 1.0))
        
        # Register UDFs
        self.medical_sentiment_udf = medical_sentiment_score
        self.urgency_udf = urgency_score
        self.emotion_udf = detect_emotion
        self.question_count_udf = count_questions
        self.complexity_udf = complexity_score
    
    def load_data_from_dynamodb(self):
        """Load conversation data from DynamoDB"""
        print("Loading data from DynamoDB...")
        
        response = self.table.scan()
        items = response.get('Items', [])
        
        # Handle pagination
        while 'LastEvaluatedKey' in response:
            response = self.table.scan(ExclusiveStartKey=response['LastEvaluatedKey'])
            items.extend(response.get('Items', []))
        
        print(f"Loaded {len(items)} records from DynamoDB")
        
        # Convert to Spark DataFrame
        df = self.spark.createDataFrame(items)
        return df
    
    def preprocess_conversations(self, df):
        """Preprocess conversation data"""
        print("🔧 Preprocessing conversation data...")
        
        # Extract conversation text
        df = df.withColumn(
            "full_conversation",
            col("conversation_text")
        )
        
        # Clean text
        df = df.withColumn(
            "cleaned_text",
            regexp_replace(
                regexp_replace(col("full_conversation"), r'[^\w\s\.\?\!]', ''),
                r'\s+', ' '
            )
        )
        
        # Extract turns (split by newlines or speaker changes)
        df = df.withColumn(
            "conversation_turns",
            split(col("cleaned_text"), r'\n+')
        )
        
        # Count turns
        df = df.withColumn(
            "num_turns",
            when(col("conversation_turns").isNotNull(), 
                 col("conversation_turns").getItem(0)).otherwise(0)
        )
        
        return df
    
    def analyze_sentiment(self, df):
        """Perform comprehensive sentiment analysis"""
        print("Analyzing sentiment...")
        
        # Apply medical sentiment scoring
        df = df.withColumn(
            "medical_sentiment",
            self.medical_sentiment_udf(col("cleaned_text"))
        )
        
        # Apply urgency scoring
        df = df.withColumn(
            "urgency_level",
            self.urgency_udf(col("cleaned_text"))
        )
        
        # Detect emotions
        df = df.withColumn(
            "dominant_emotion",
            self.emotion_udf(col("cleaned_text"))
        )
        
        # Count questions
        df = df.withColumn(
            "question_count",
            self.question_count_udf(col("cleaned_text"))
        )
        
        # Calculate complexity
        df = df.withColumn(
            "complexity",
            self.complexity_udf(col("cleaned_text"))
        )
        
        # Categorize sentiment
        df = df.withColumn(
            "sentiment_category",
            when(col("medical_sentiment") > 0.3, "Positive")
            .when(col("medical_sentiment") < -0.3, "Negative")
            .otherwise("Neutral")
        )
        
        # Categorize urgency
        df = df.withColumn(
            "urgency_category",
            when(col("urgency_level") > 0.7, "Critical")
            .when(col("urgency_level") > 0.4, "High")
            .when(col("urgency_level") > 0.2, "Medium")
            .otherwise("Low")
        )
        
        return df
    
    def perform_topic_modeling(self, df):
        """Perform LDA topic modeling on conversations"""
        print("Performing topic modeling...")
        
        # Tokenization pipeline
        tokenizer = Tokenizer(inputCol="cleaned_text", outputCol="words")
        remover = StopWordsRemover(inputCol="words", outputCol="filtered_words")
        vectorizer = CountVectorizer(
            inputCol="filtered_words", 
            outputCol="features",
            vocabSize=1000,
            minDF=2.0
        )
        
        # LDA model
        lda = LDA(
            k=5,  # Number of topics
            maxIter=20,
            featuresCol="features",
            seed=42
        )
        
        # Build pipeline
        pipeline = Pipeline(stages=[tokenizer, remover, vectorizer, lda])
        
        # Fit model
        model = pipeline.fit(df)
        
        # Transform data
        topics_df = model.transform(df)
        
        # Extract topic distributions
        lda_model = model.stages[-1]
        topics = lda_model.describeTopics(maxTermsPerTopic=10)
        vocab = model.stages[-2].vocabulary
        
        print("\nDiscovered Topics:")
        for topic_idx, row in enumerate(topics.collect()):
            print(f"\nTopic {topic_idx}:")
            terms = [vocab[idx] for idx in row['termIndices']]
            weights = row['termWeights']
            for term, weight in zip(terms, weights):
                print(f"  - {term}: {weight:.4f}")
        
        return topics_df, lda_model
    
    def compute_aggregated_metrics(self, df):
        """Compute aggregated metrics and statistics"""
        print("Computing aggregated metrics...")
        
        # Overall statistics
        overall_stats = df.select(
            avg("medical_sentiment").alias("avg_sentiment"),
            avg("urgency_level").alias("avg_urgency"),
            avg("complexity").alias("avg_complexity"),
            avg("question_count").alias("avg_questions"),
            count("*").alias("total_conversations")
        ).collect()[0]
        
        # Sentiment distribution
        sentiment_dist = df.groupBy("sentiment_category") \
            .agg(count("*").alias("count")) \
            .collect()
        
        # Emotion distribution
        emotion_dist = df.groupBy("dominant_emotion") \
            .agg(count("*").alias("count")) \
            .collect()
        
        # Urgency distribution
        urgency_dist = df.groupBy("urgency_category") \
            .agg(count("*").alias("count")) \
            .collect()
        
        # Score correlation analysis
        score_cols = [
            "intent_recognition_score",
            "response_correctness_score",
            "error_handling_score",
            "tone_appropriateness_score",
            "safety_compliance_score",
            "conversation_flow_score"
        ]
        
        # Filter columns that exist
        existing_score_cols = [c for c in score_cols if c in df.columns]
        
        if existing_score_cols:
            score_stats = df.select(
                *[avg(col(c)).alias(f"avg_{c}") for c in existing_score_cols]
            ).collect()[0]
        else:
            score_stats = None
        
        return {
            "overall_stats": overall_stats.asDict(),
            "sentiment_distribution": {row['sentiment_category']: row['count'] 
                                      for row in sentiment_dist},
            "emotion_distribution": {row['dominant_emotion']: row['count'] 
                                    for row in emotion_dist},
            "urgency_distribution": {row['urgency_category']: row['count'] 
                                    for row in urgency_dist},
            "score_statistics": score_stats.asDict() if score_stats else {}
        }
    
    def identify_patterns_and_anomalies(self, df):
        """Identify conversation patterns and anomalies"""
        print("🔍 Identifying patterns and anomalies...")
        
        # High urgency + negative sentiment conversations
        critical_conversations = df.filter(
            (col("urgency_level") > 0.6) & (col("medical_sentiment") < -0.3)
        ).select(
            "conversation_id",
            "conversation_title",
            "urgency_level",
            "medical_sentiment",
            "dominant_emotion"
        )
        
        # Conversations with many questions but low engagement
        low_engagement = df.filter(
            (col("question_count") > 5) & (col("complexity") < 0.3)
        )
        
        # Outlier detection using statistical methods
        sentiment_stats = df.select(
            avg("medical_sentiment").alias("mean"),
            stddev("medical_sentiment").alias("std")
        ).collect()[0]
        
        outliers = df.filter(
            (col("medical_sentiment") > sentiment_stats['mean'] + 2 * sentiment_stats['std']) |
            (col("medical_sentiment") < sentiment_stats['mean'] - 2 * sentiment_stats['std'])
        )
        
        return {
            "critical_conversations": critical_conversations.count(),
            "low_engagement": low_engagement.count(),
            "sentiment_outliers": outliers.count()
        }
    
    def generate_insights(self, df, metrics, patterns):
        """Generate actionable insights from analysis"""
        print("Generating insights...")
        
        insights = []
        
        # Insight 1: Sentiment trends
        if metrics['overall_stats']['avg_sentiment'] < -0.2:
            insights.append({
                "type": "warning",
                "category": "sentiment",
                "message": "Overall conversation sentiment is negative. Consider reviewing agent responses for empathy and understanding.",
                "priority": "high"
            })
        
        # Insight 2: Urgency handling
        if metrics['urgency_distribution'].get('Critical', 0) > 0:
            critical_pct = (metrics['urgency_distribution']['Critical'] / 
                          metrics['overall_stats']['total_conversations']) * 100
            insights.append({
                "type": "alert",
                "category": "urgency",
                "message": f"{critical_pct:.1f}% of conversations show critical urgency. Ensure proper escalation protocols.",
                "priority": "critical"
            })
        
        # Insight 3: Emotion patterns
        dominant_emotions = sorted(
            metrics['emotion_distribution'].items(),
            key=lambda x: x[1],
            reverse=True
        )
        if dominant_emotions:
            top_emotion = dominant_emotions[0][0]
            insights.append({
                "type": "info",
                "category": "emotion",
                "message": f"Most common emotion: {top_emotion}. Tailor responses accordingly.",
                "priority": "medium"
            })
        
        # Insight 4: Complexity analysis
        if metrics['overall_stats']['avg_complexity'] > 0.7:
            insights.append({
                "type": "suggestion",
                "category": "complexity",
                "message": "Conversations show high complexity. Consider simplifying medical terminology.",
                "priority": "medium"
            })
        
        # Insight 5: Pattern detection
        if patterns['critical_conversations'] > 0:
            insights.append({
                "type": "alert",
                "category": "patterns",
                "message": f"Identified {patterns['critical_conversations']} critical conversations requiring immediate review.",
                "priority": "high"
            })
        
        return insights
    
    def save_results_to_dynamodb(self, df, metrics, insights):
        """Save analysis results back to DynamoDB"""
        print("Saving results to DynamoDB...")
        
        # Create results table if it doesn't exist
        results_table_name = "conversation_analytics_results"
        
        try:
            results_table = self.dynamodb.Table(results_table_name)
            results_table.load()
        except:
            results_table = self.dynamodb.create_table(
                TableName=results_table_name,
                KeySchema=[
                    {'AttributeName': 'analysis_id', 'KeyType': 'HASH'}
                ],
                AttributeDefinitions=[
                    {'AttributeName': 'analysis_id', 'AttributeType': 'S'}
                ],
                BillingMode='PAY_PER_REQUEST'
            )
            results_table.wait_until_exists()
        
        # Prepare summary result
        analysis_result = {
            'analysis_id': f"analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            'timestamp': datetime.now().isoformat(),
            'metrics': json.dumps(metrics, default=str),
            'insights': json.dumps(insights),
            'total_conversations_analyzed': metrics['overall_stats']['total_conversations']
        }
        
        # Save to DynamoDB
        results_table.put_item(Item=analysis_result)
        
        # Also update individual conversations with sentiment scores
        conversations_with_sentiment = df.select(
            "conversation_id",
            "medical_sentiment",
            "urgency_level",
            "dominant_emotion",
            "sentiment_category",
            "urgency_category",
            "complexity"
        ).collect()
        
        for row in conversations_with_sentiment[:100]:  # Limit batch update
            try:
                self.table.update_item(
                    Key={'conversation_id': row['conversation_id']},
                    UpdateExpression="""
                        SET medical_sentiment = :sentiment,
                            urgency_level = :urgency,
                            dominant_emotion = :emotion,
                            sentiment_category = :sent_cat,
                            urgency_category = :urg_cat,
                            complexity_score = :complexity
                    """,
                    ExpressionAttributeValues={
                        ':sentiment': float(row['medical_sentiment']) if row['medical_sentiment'] else 0.0,
                        ':urgency': float(row['urgency_level']) if row['urgency_level'] else 0.0,
                        ':emotion': row['dominant_emotion'],
                        ':sent_cat': row['sentiment_category'],
                        ':urg_cat': row['urgency_category'],
                        ':complexity': float(row['complexity']) if row['complexity'] else 0.0
                    }
                )
            except Exception as e:
                print(f"Error updating conversation {row['conversation_id']}: {e}")
        
        print(f"Results saved with analysis_id: {analysis_result['analysis_id']}")
        return analysis_result['analysis_id']
    
    def run_complete_analysis(self):
        """Run the complete big data analysis pipeline"""
        print("Starting Healthcare Conversation Big Data Analysis\n")
        
        # Step 1: Load data
        df = self.load_data_from_dynamodb()
        
        # Step 2: Preprocess
        df = self.preprocess_conversations(df)
        
        # Step 3: Sentiment analysis
        df = self.analyze_sentiment(df)
        
        # Step 4: Topic modeling
        df_with_topics, lda_model = self.perform_topic_modeling(df)
        
        # Step 5: Compute metrics
        metrics = self.compute_aggregated_metrics(df_with_topics)
        
        # Step 6: Identify patterns
        patterns = self.identify_patterns_and_anomalies(df_with_topics)
        
        # Step 7: Generate insights
        insights = self.generate_insights(df_with_topics, metrics, patterns)
        
        # Step 8: Save results
        analysis_id = self.save_results_to_dynamodb(df_with_topics, metrics, insights)
        
        # Print summary
        print("\n" + "="*60)
        print("ANALYSIS COMPLETE")
        print("="*60)
        print(f"Analysis ID: {analysis_id}")
        print(f"Total Conversations: {metrics['overall_stats']['total_conversations']}")
        print(f"Average Sentiment: {metrics['overall_stats']['avg_sentiment']:.3f}")
        print(f"Average Urgency: {metrics['overall_stats']['avg_urgency']:.3f}")
        print(f"\nKey Insights:")
        for i, insight in enumerate(insights, 1):
            print(f"{i}. [{insight['priority'].upper()}] {insight['message']}")
        print("="*60)
        
        return {
            'analysis_id': analysis_id,
            'metrics': metrics,
            'insights': insights,
            'patterns': patterns
        }


# Main execution
if __name__ == "__main__":
    analyzer = HealthcareConversationAnalyzer()
    results = analyzer.run_complete_analysis()
    
    # Stop Spark session
    analyzer.spark.stop()
    
    print("\nAnalysis pipeline completed successfully!")