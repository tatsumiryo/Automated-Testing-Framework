import boto3
import yaml

# Load YAML
with open("config.yml", "r") as f:
    config = yaml.safe_load(f)

# Connect to DynamoDB
dynamodb = boto3.resource('dynamodb', region_name=config["aws"]["region"])
table = dynamodb.Table(config["aws"]["table_name"])

# Example: Put an item
table.put_item(Item={"id": "1", "name": "Alice"})

# Example: Get the item
response = table.get_item(Key={"id": "1"})
print(response["Item"])
