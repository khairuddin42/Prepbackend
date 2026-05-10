#!/usr/bin/env python3
"""
Test script for Groq API integration in AI Exam-Prep Tutor.
This script tests the new Groq API functions without requiring authentication.
"""

import asyncio
import sys
import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Add the app directory to the Python path
sys.path.append(str(Path(__file__).parent / "app"))

from app.routers.ai_processing import (
    _summarize_with_groq_api,
    _generate_quiz_with_groq_api,
    _generate_flashcards_with_groq_api,
    chunk_text
)
from app.config import settings

async def test_groq_summarization():
    """Test Groq API summarization."""
    print("Testing Groq API Summarization...")
    
    test_text = """
    Artificial Intelligence (AI) is a branch of computer science that aims to create intelligent machines 
    that can perform tasks that typically require human intelligence. These tasks include learning, 
    reasoning, problem-solving, perception, and language understanding. Machine learning is a subset 
    of AI that focuses on algorithms that can learn and improve from experience without being explicitly 
    programmed. Deep learning, a subset of machine learning, uses neural networks with multiple layers 
    to model and understand complex patterns in data. AI has applications in various fields including 
    healthcare, finance, transportation, and entertainment. The development of AI raises important 
    questions about ethics, privacy, and the future of work.
    """
    
    try:
        chunks = chunk_text(test_text)
        summary = await _summarize_with_groq_api(chunks, "normal")
        print(f"SUCCESS: Summarization successful!")
        print(f"Summary: {summary[:200]}...")
        return True
    except Exception as e:
        print(f"ERROR: Summarization failed: {e}")
        return False

async def test_groq_quiz_generation():
    """Test Groq API quiz generation."""
    print("\nTesting Groq API Quiz Generation...")
    
    test_text = """
    Photosynthesis is the process by which plants convert light energy into chemical energy. 
    This process occurs in the chloroplasts of plant cells, specifically in structures called thylakoids. 
    During photosynthesis, plants absorb carbon dioxide from the atmosphere and water from the soil. 
    Using sunlight as the energy source, these raw materials are converted into glucose and oxygen. 
    The glucose serves as food for the plant, while oxygen is released into the atmosphere as a byproduct. 
    This process is crucial for life on Earth as it produces the oxygen we breathe and forms the base 
    of most food chains. Photosynthesis can be divided into two main stages: the light-dependent 
    reactions and the light-independent reactions (Calvin cycle).
    """
    
    try:
        questions = await _generate_quiz_with_groq_api(test_text)
        print(f"SUCCESS: Quiz generation successful!")
        print(f"Generated {len(questions)} questions")
        if questions:
            print(f"Sample question: {questions[0]['question'][:100]}...")
        return True
    except Exception as e:
        print(f"ERROR: Quiz generation failed: {e}")
        return False

async def test_groq_flashcard_generation():
    """Test Groq API flashcard generation."""
    print("\nTesting Groq API Flashcard Generation...")
    
    test_text = """
    Machine learning is a subset of artificial intelligence that focuses on algorithms that can learn 
    and improve from experience without being explicitly programmed. There are three main types of 
    machine learning: supervised learning, unsupervised learning, and reinforcement learning. 
    Supervised learning uses labeled training data to learn a mapping from inputs to outputs. 
    Unsupervised learning finds hidden patterns in data without labeled examples. Reinforcement 
    learning learns through interaction with an environment, receiving rewards or penalties for actions.
    """
    
    try:
        flashcards = await _generate_flashcards_with_groq_api(test_text, 5)
        print(f"SUCCESS: Flashcard generation successful!")
        print(f"Generated {len(flashcards)} flashcards")
        if flashcards:
            print(f"Sample flashcard: {flashcards[0]['front'][:50]}...")
        return True
    except Exception as e:
        print(f"ERROR: Flashcard generation failed: {e}")
        return False

async def main():
    """Run all Groq API tests."""
    print("Starting Groq API Integration Tests")
    print("=" * 50)
    
    # Check if Groq API key is configured
    if not settings.GROQ_API_KEY:
        print("ERROR: GROQ_API_KEY not found in environment variables")
        print("Please set GROQ_API_KEY in your .env file")
        return
    
    print(f"Using Groq model: {settings.GROQ_MODEL}")
    print(f"API key configured: {'*' * 20}{settings.GROQ_API_KEY[-4:]}")
    
    # Run tests
    results = []
    results.append(await test_groq_summarization())
    results.append(await test_groq_quiz_generation())
    results.append(await test_groq_flashcard_generation())
    
    # Summary
    print("\n" + "=" * 50)
    print("Test Results Summary:")
    print(f"Passed: {sum(results)}/{len(results)}")
    print(f"Failed: {len(results) - sum(results)}/{len(results)}")
    
    if all(results):
        print("All tests passed! Groq API integration is working correctly.")
    else:
        print("Some tests failed. Check the error messages above.")

if __name__ == "__main__":
    asyncio.run(main())
