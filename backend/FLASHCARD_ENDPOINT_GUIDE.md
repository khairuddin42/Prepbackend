# Flashcard Generation Endpoint Guide

## Overview
The flashcard generation endpoint uses the **phi-3.5-mini** model to generate educational flashcards from uploaded lecture notes. It automatically creates term/definition or question/answer pairs to help students study effectively.

---

## Endpoint: POST `/flashcards/{file_id}`

### Description
Generate flashcards for a specific file. The endpoint:
- ✅ Returns cached flashcards if they already exist
- ✅ Fetches file content with ownership verification
- ✅ For long texts (>3000 chars), summarizes first for focused flashcards
- ✅ Uses phi-3.5-mini model to generate flashcards
- ✅ Validates and normalizes JSON output
- ✅ Saves flashcards to database

### Authentication
**Required**: Bearer token in Authorization header

### Path Parameters
- `file_id` (string, required): UUID of the uploaded file

### Query Parameters
- `count` (integer, optional): Number of flashcards to generate
  - **Default**: 10
  - **Minimum**: 5
  - **Maximum**: 30
  - **Example**: `?count=15`

---

## Request Examples

### Basic Request (Default 10 flashcards)
```bash
curl -X POST "http://localhost:8000/flashcards/{file_id}" \
  -H "Authorization: Bearer YOUR_AUTH_TOKEN" \
  -H "Content-Type: application/json"
```

### Custom Count (15 flashcards)
```bash
curl -X POST "http://localhost:8000/flashcards/{file_id}?count=15" \
  -H "Authorization: Bearer YOUR_AUTH_TOKEN" \
  -H "Content-Type: application/json"
```

### Minimum Flashcards (5 cards)
```bash
curl -X POST "http://localhost:8000/flashcards/{file_id}?count=5" \
  -H "Authorization: Bearer YOUR_AUTH_TOKEN" \
  -H "Content-Type: application/json"
```

### Maximum Flashcards (30 cards)
```bash
curl -X POST "http://localhost:8000/flashcards/{file_id}?count=30" \
  -H "Authorization: Bearer YOUR_AUTH_TOKEN" \
  -H "Content-Type: application/json"
```

---

## Success Response (200 OK)

### First Generation (Not Cached)
```json
{
  "flashcard_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "cards": [
    {
      "front": "What is Photosynthesis?",
      "back": "The process by which plants convert light energy into chemical energy"
    },
    {
      "front": "Chloroplasts",
      "back": "Organelles in plant cells where photosynthesis occurs"
    },
    {
      "front": "What are the main products of photosynthesis?",
      "back": "Glucose (sugar) and oxygen"
    },
    {
      "front": "Carbon Dioxide",
      "back": "Gas absorbed by plants from the atmosphere during photosynthesis"
    },
    {
      "front": "What is the Calvin Cycle?",
      "back": "The light-independent reactions of photosynthesis that produce glucose"
    },
    {
      "front": "Thylakoids",
      "back": "Membrane-bound compartments inside chloroplasts where light reactions occur"
    },
    {
      "front": "What is the primary energy source for photosynthesis?",
      "back": "Sunlight"
    },
    {
      "front": "Stomata",
      "back": "Tiny pores on plant leaves that allow gas exchange"
    },
    {
      "front": "What are the two main stages of photosynthesis?",
      "back": "Light-dependent reactions and light-independent reactions (Calvin cycle)"
    },
    {
      "front": "Chlorophyll",
      "back": "Green pigment in plants that absorbs light energy for photosynthesis"
    }
  ],
  "card_count": 10,
  "cached": false,
  "filename": "photosynthesis_lecture.pdf"
}
```

### Subsequent Requests (Cached)
```json
{
  "flashcard_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "cards": [
    {
      "front": "What is Photosynthesis?",
      "back": "The process by which plants convert light energy into chemical energy"
    },
    {
      "front": "Chloroplasts",
      "back": "Organelles in plant cells where photosynthesis occurs"
    }
    // ... (same flashcards as before)
  ],
  "card_count": 10,
  "cached": true,
  "created_at": "2024-01-15T10:30:00.000Z"
}
```

---

## Error Responses

### 404 Not Found - File Not Found
```json
{
  "detail": "File not found or access denied"
}
```

### 422 Unprocessable Entity - No Text Content
```json
{
  "detail": "File has no extractable text"
}
```

### 422 Validation Error - Invalid Count Parameter
```json
{
  "detail": [
    {
      "loc": ["query", "count"],
      "msg": "ensure this value is greater than or equal to 5",
      "type": "value_error.number.not_ge"
    }
  ]
}
```

### 502 Bad Gateway - AI Model Error
```json
{
  "detail": "AI service error - unable to generate flashcards at this time"
}
```

### 500 Internal Server Error - General Error
```json
{
  "detail": "Flashcard generation failed: [error details]"
}
```

---

## Endpoint: DELETE `/flashcards/{file_id}`

### Description
Delete saved flashcards for a file to force regeneration on next request.

### Request Example
```bash
curl -X DELETE "http://localhost:8000/flashcards/{file_id}" \
  -H "Authorization: Bearer YOUR_AUTH_TOKEN" \
  -H "Content-Type: application/json"
```

### Success Response (200 OK)
```json
{
  "message": "Flashcards deleted successfully. Call flashcards endpoint again to generate new flashcards.",
  "file_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
}
```

### Error Response (404 Not Found)
```json
{
  "detail": "No flashcards found for this file"
}
```

---

## Implementation Details

### AI Model
- **Model**: `microsoft/Phi-3.5-mini-instruct`
- **Type**: Text generation (causal LM)
- **Fallback**: Intelligent rule-based flashcard generation if model fails
- **GPU**: Automatically uses GPU if available, falls back to CPU

### Prompt Template
```
Create {count} flashcards from the following text. Each flashcard should have a front (term or question) and back (definition or answer).

Text: {text}

Return ONLY a valid JSON array in this exact format:
[
  {"front": "Term or question", "back": "Definition or answer"},
  {"front": "Term or question", "back": "Definition or answer"}
]

IMPORTANT: 
- Return ONLY the JSON array, no other text
- Each flashcard must have "front" and "back" fields
- Make flashcards clear, concise, and educational
- Cover key concepts from the text
```

### Text Processing Strategy
1. **Short Text (<3000 chars)**: Generate flashcards directly from full text
2. **Long Text (≥3000 chars)**:
   - Check for existing summary
   - If no summary exists, generate one first
   - Use summary for flashcard generation to keep cards focused

### JSON Validation
The endpoint performs strict validation:
- ✅ Must be valid JSON array
- ✅ Each card must have "front" and "back" fields
- ✅ Front text must be at least 3 characters
- ✅ Back text must be at least 3 characters
- ✅ Minimum 3 valid flashcards required
- ✅ Automatic cleanup of markdown formatting

### Fallback Strategy
If AI model fails, an intelligent fallback system:
1. **Pattern Detection**: Identifies "is", "are", "means" for definitions
2. **Key Term Extraction**: Extracts capitalized or long words as key terms
3. **Context-Based Questions**: Creates fill-in-the-blank style flashcards
4. **Frequency Analysis**: Uses most frequent important words
5. **Ultimate Fallback**: Basic flashcards covering main topics

---

## Usage Notes

### Best Practices
- 📖 **Start with defaults**: Use default count (10) for most documents
- 📊 **Adjust based on content**: Use 15-20 for comprehensive study materials
- 🔄 **Cache awareness**: Subsequent requests return cached flashcards instantly
- 🗑️ **Force regeneration**: Delete flashcards to generate new ones
- 📝 **Text quality**: Better source text = better flashcards

### Performance Tips
- ⚡ First generation may take 10-30 seconds depending on hardware
- 🚀 Cached requests return in <1 second
- 💾 GPU acceleration significantly speeds up generation
- 📉 Longer texts are auto-summarized to improve generation speed

### Limitations
- ⚠️ Maximum 30 flashcards per request (to manage generation time)
- ⚠️ Minimum 5 flashcards (to ensure useful study set)
- ⚠️ Model may occasionally produce suboptimal cards (use delete to regenerate)
- ⚠️ Very technical content may benefit from manual review

---

## Integration Example (Python)

```python
import requests

# Configuration
BASE_URL = "http://localhost:8000"
AUTH_TOKEN = "your_auth_token_here"
FILE_ID = "a1b2c3d4-e5f6-7890-abcd-ef1234567890"

# Headers
headers = {
    "Authorization": f"Bearer {AUTH_TOKEN}",
    "Content-Type": "application/json"
}

# Generate flashcards (15 cards)
response = requests.post(
    f"{BASE_URL}/flashcards/{FILE_ID}?count=15",
    headers=headers
)

if response.status_code == 200:
    data = response.json()
    print(f"Generated {data['card_count']} flashcards")
    print(f"Cached: {data['cached']}")
    
    # Display flashcards
    for i, card in enumerate(data['cards'], 1):
        print(f"\nCard {i}:")
        print(f"  Front: {card['front']}")
        print(f"  Back: {card['back']}")
else:
    print(f"Error: {response.status_code}")
    print(response.json())
```

---

## Testing

### Test with Sample Text
```bash
# 1. Upload a file first (get file_id from response)
# 2. Generate flashcards
curl -X POST "http://localhost:8000/flashcards/{file_id}?count=10" \
  -H "Authorization: Bearer YOUR_TOKEN"

# 3. Verify cached response (should be instant)
curl -X POST "http://localhost:8000/flashcards/{file_id}" \
  -H "Authorization: Bearer YOUR_TOKEN"

# 4. Delete flashcards
curl -X DELETE "http://localhost:8000/flashcards/{file_id}" \
  -H "Authorization: Bearer YOUR_TOKEN"

# 5. Generate new flashcards
curl -X POST "http://localhost:8000/flashcards/{file_id}?count=20" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

---

## Database Schema

The flashcards are stored in the `flashcards` table:

```sql
CREATE TABLE flashcards (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    file_id UUID NOT NULL REFERENCES files(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    cards JSONB NOT NULL,  -- Array of {front, back} objects
    created_at TIMESTAMPTZ DEFAULT NOW()
);
```

### JSONB Structure
```json
[
  {"front": "string", "back": "string"},
  {"front": "string", "back": "string"}
]
```

---

## Support & Troubleshooting

### Common Issues

**Issue**: "AI service error"
- **Solution**: Check model is downloaded, GPU memory, or wait for HF API

**Issue**: Flashcards are too generic
- **Solution**: Delete and regenerate, or try with full text instead of summary

**Issue**: Count validation error
- **Solution**: Ensure count is between 5-30

**Issue**: "File not found"
- **Solution**: Verify file_id exists and user has access

---

## Version History

- **v1.0** (2024): Initial flashcard generation with phi-3.5-mini
  - POST `/flashcards/{file_id}` endpoint
  - DELETE `/flashcards/{file_id}` endpoint
  - Count query parameter (5-30)
  - Automatic text summarization for long content
  - Intelligent fallback generation
  - JSON validation and normalization


