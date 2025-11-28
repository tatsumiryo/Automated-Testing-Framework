import requests
import time

BASE_URL = "http://52.23.188.49:5000"

print("🧪 Running tests against EC2 instance...")
print(f"Target: {BASE_URL}\n")

# Test 1: Simple tests
tests = [
    ("frustrated", "I've been waiting FOREVER! I need help NOW!"),
    ("elderly", "Hello... I need... to book an appointment... please"),
    ("non_native", "I am needing appointment with doctor for headache"),
    ("fast_speaker", "HiIneedanappointmentASAPtomorrowmorning"),
    ("vague", "I need help with something")
]

for persona, prompt in tests:
    print(f"Testing {persona} persona...")
    response = requests.post(
        f"{BASE_URL}/test-single",
        json={"persona_type": persona, "test_prompt": prompt}
    )
    print(f"  Score: {response.json()['overall_score']:.2%}")
    time.sleep(2)

print("\n✅ All tests completed! Check your dashboard.")