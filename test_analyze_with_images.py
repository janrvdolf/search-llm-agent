#!/usr/bin/env python3
"""
Test script for the analyze tool with image support
"""

import os
import json
import requests
from agent import SimpleLangChainAgent


def download_test_image():
    """Download a test image for analysis"""
    # Create test directory
    os.makedirs("test_images", exist_ok=True)

    # Download a sample image (using a placeholder image service)
    image_url = "https://via.placeholder.com/400x300/0000FF/FFFFFF?text=Test+Chart"

    try:
        response = requests.get(image_url)
        response.raise_for_status()

        # Save the image
        with open("test_images/test_chart.png", "wb") as f:
            f.write(response.content)
        print("✅ Downloaded test chart image")

        # Also create a simple diagram using another placeholder
        diagram_url = (
            "https://via.placeholder.com/600x400/FF0000/FFFFFF?text=Sales+Growth+2024"
        )
        response = requests.get(diagram_url)
        with open("test_images/sales_diagram.png", "wb") as f:
            f.write(response.content)
        print("✅ Downloaded sales diagram image")

    except Exception as e:
        print(f"⚠️ Could not download test images: {e}")
        print("Creating a simple text file as fallback...")

        # Create a text file describing what the image would show
        with open("test_images/chart_description.txt", "w") as f:
            f.write(
                """This is a placeholder for an image analysis test.
In a real scenario, this would be an actual chart or diagram image.
The image would show data trends, visual elements, and other graphical information
that Claude could analyze and describe."""
            )


def test_analyze_with_images():
    """Test the analyze tool with both text files and images"""

    # Download test images
    download_test_image()

    # Create additional test files
    os.makedirs("test_files", exist_ok=True)

    # Create a JSON data file
    data = {
        "sales": [
            {"month": "Jan", "revenue": 50000, "growth": 5},
            {"month": "Feb", "revenue": 52500, "growth": 5},
            {"month": "Mar", "revenue": 55125, "growth": 5},
            {"month": "Apr", "revenue": 53000, "growth": -3.8},
            {"month": "May", "revenue": 58000, "growth": 9.4},
        ],
        "summary": {
            "total_revenue": 268625,
            "average_growth": 4.12,
            "best_month": "May",
            "worst_month": "Apr",
        },
    }

    with open("test_files/sales_data.json", "w") as f:
        json.dump(data, f, indent=2)

    print("\n✅ Test files created successfully!")
    print("\nCreated files:")
    print("- test_files/sales_data.json")
    print("- test_images/test_chart.png")
    print("- test_images/sales_diagram.png")

    # Initialize the agent
    print("\n🤖 Initializing agent...")
    agent = SimpleLangChainAgent()

    # Test queries
    test_queries = [
        # Text file analysis
        {
            "file": "test_files/sales_data.json",
            "query": "Analyze the sales trends and identify any patterns or concerns",
        },
        # Image analysis (if images were downloaded)
        {
            "file": "test_images/test_chart.png",
            "query": "Describe what you see in this image, including colors, text, and layout",
        },
        {
            "file": "test_images/sales_diagram.png",
            "query": "What information does this diagram convey? Describe the visual elements",
        },
    ]

    print("\n🧪 Running analysis tests...\n")

    for test in test_queries:
        file_path = test["file"]
        query = test["query"]

        # Skip image tests if the images don't exist
        if file_path.endswith((".png", ".jpg")) and not os.path.exists(file_path):
            print(f"\n⚠️ Skipping {file_path} - file not found")
            continue

        print(f"\n{'='*60}")
        print(f"📄 File: {file_path}")
        print(f"❓ Query: {query}")
        print(f"{'='*60}")

        # Use the agent to analyze
        result = agent.chat(f'analyze("{file_path}", "{query}")')
        print(result)

    # Demonstrate image search and analysis workflow
    print(f"\n\n{'='*60}")
    print("🔍 BONUS: Image Search + Analysis Workflow")
    print(f"{'='*60}")

    # Search for images
    print("\n1️⃣ Searching for images...")
    search_result = agent.chat('search("cute puppies", "images", 3)')
    print(search_result)

    # Download the images
    print("\n2️⃣ Downloading images...")
    download_result = agent.chat('download("puppies")')
    print(download_result)

    # Note about analyzing downloaded images
    print("\n3️⃣ To analyze downloaded images, you would use:")
    print(
        '   analyze("downloads/puppies_01_[hash].jpg", "Describe this puppy and its surroundings")'
    )

    print("\n✅ Test completed!")


if __name__ == "__main__":
    test_analyze_with_images()
