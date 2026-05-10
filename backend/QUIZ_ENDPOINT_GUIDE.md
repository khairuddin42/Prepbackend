# Quiz Generation Endpoint Guide

## Overview
The quiz generation endpoint (`POST /quiz/{file_id}`) generates multiple-choice questions from uploaded lecture notes using AI models.

## Features
- ✅ **Protected endpoint** with Supabase authentication
- ✅ **Caching** - returns existing quiz if already generated
- ✅ **AI Integration** - uses flan-t5-base model (local + HF API fallback)
- ✅ **JSON Validation** - validates and cleans AI responses
- ✅ **Error Handling** - graceful fallbacks and helpful error messages
- ✅ **Database Storage** - saves quizzes for future retrieval
- ✅ **Smart Text Processing** - uses summaries for long texts

## Endpoints

### 1. Generate Quiz
```http
POST /quiz/{file_id}
Authorization: Bearer <supabase_jwt_token>
```

**Response (New Quiz):**
```json
{
  "quiz_id": "uuid-string",
  "questions": [
    {
      "question": "What is the main topic discussed?",
      "options": ["Option A", "Option B", "Option C", "Option D"],
      "answer_index": 1
    }
  ],
  "cached": false,
  "filename": "lecture_notes.pdf",
  "question_count": 4
}
```

**Response (Cached Quiz):**
```json
{
  "quiz_id": "uuid-string",
  "questions": [...],
  "cached": true,
  "created_at": "2024-01-01T12:00:00Z"
}
```

### 2. Delete Quiz
```http
DELETE /quiz/{file_id}
Authorization: Bearer <supabase_jwt_token>
```

**Response:**
```json
{
  "message": "Quiz deleted successfully. Call quiz endpoint again to generate a new quiz.",
  "file_id": "file-uuid"
}
```

### 3. Test Quiz Generation
```http
POST /test-ai-quiz
```

**Response:**
```json
{
  "message": "AI quiz generation test completed",
  "original_text_length": 500,
  "questions": [...],
  "question_count": 4,
  "is_ai_generated": true
}
```

## Testing with cURL

### 1. Test AI Quiz Generation (No Auth Required)
```bash
curl -X POST "http://localhost:8000/test-ai-quiz" \
  -H "Content-Type: application/json"
```

### 2. Generate Quiz for File (Auth Required)
```bash
# First, get a Supabase JWT token from your frontend/auth system
# Then use it in the Authorization header

curl -X POST "http://localhost:8000/quiz/your-file-id-here" \
  -H "Authorization: Bearer YOUR_SUPABASE_JWT_TOKEN" \
  -H "Content-Type: application/json"
```

### 3. Delete Quiz
```bash
curl -X DELETE "http://localhost:8000/quiz/your-file-id-here" \
  -H "Authorization: Bearer YOUR_SUPABASE_JWT_TOKEN" \
  -H "Content-Type: application/json"
```

## Example Quiz Response
```json
{
  "quiz_id": "123e4567-e89b-12d3-a456-426614174000",
  "questions": [
    {
      "question": "What is photosynthesis?",
      "options": [
        "Process by which plants convert light energy to chemical energy",
        "Process by which animals digest food",
        "Process by which cells divide",
        "Process by which DNA replicates"
      ],
      "answer_index": 0
    },
    {
      "question": "Where does photosynthesis occur in plant cells?",
      "options": [
        "Mitochondria",
        "Chloroplasts",
        "Nucleus",
        "Cell wall"
      ],
      "answer_index": 1
    },
    {
      "question": "What are the main inputs for photosynthesis?",
      "options": [
        "Glucose and oxygen",
        "Carbon dioxide and water",
        "ATP and NADPH",
        "Chlorophyll and sunlight"
      ],
      "answer_index": 1
    },
    {
      "question": "What is released as a byproduct of photosynthesis?",
      "options": [
        "Carbon dioxide",
        "Water",
        "Oxygen",
        "Glucose"
      ],
      "answer_index": 2
    }
  ],
  "cached": false,
  "filename": "biology_lecture.pdf",
  "question_count": 4
}
```

## Error Handling

### Common Error Responses

**401 Unauthorized:**
```json
{
  "detail": "Invalid authentication token"
}
```

**404 Not Found:**
```json
{
  "detail": "File not found or access denied"
}
```

**422 Unprocessable Entity:**
```json
{
  "detail": "File has no extractable text"
}
```

**502 Bad Gateway:**
```json
{
  "detail": "AI service error - unable to generate quiz at this time"
}
```

**500 Internal Server Error:**
```json
{
  "detail": "Quiz generation failed: [specific error message]"
}
```

## AI Model Details

### Primary Model: flan-t5-base
- **Type**: Text-to-text generation
- **Provider**: Google (via Hugging Face)
- **Use Case**: Question generation from text
- **Fallback**: Simple rule-based question generation

### Prompt Template
```
From the following text, produce 4 multiple-choice questions about the most important points. Return a JSON array with fields question, options (4 items), and answer_index (0-3).

Text: [INPUT_TEXT]

Return only valid JSON in this format:
[
  {"question": "What is the main topic?", "options": ["Option A", "Option B", "Option C", "Option D"], "answer_index": 1},
  {"question": "Which statement is true?", "options": ["A", "B", "C", "D"], "answer_index": 0}
]
```

### JSON Validation
- Validates required fields: `question`, `options`, `answer_index`
- Ensures `answer_index` is within valid range (0-3)
- Cleans and formats question text
- Attempts JSON extraction from malformed responses
- Falls back to simple Q&A if validation fails

## Database Schema

### Quizzes Table
```sql
CREATE TABLE quizzes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    file_id UUID NOT NULL REFERENCES files(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    questions JSONB NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
```

### Example JSONB Structure
```json
[
  {
    "question": "What is...?",
    "options": ["A", "B", "C", "D"],
    "answer_index": 1
  }
]
```

## Security Features

- **Row Level Security (RLS)** enabled on quizzes table
- **User isolation** - users can only access their own quizzes
- **JWT validation** for all protected endpoints
- **File ownership verification** before quiz generation

## Performance Considerations

- **Caching** - existing quizzes are returned immediately
- **Smart text processing** - uses summaries for texts > 2000 characters
- **Chunking** - handles large texts by processing in chunks
- **GPU acceleration** - uses CUDA if available
- **Timeout handling** - 30-second timeout for API calls

## Troubleshooting

### Common Issues

1. **"AI service error"** - Check if transformers/torch are installed
2. **"Invalid JSON format"** - Model returned malformed JSON (automatic retry)
3. **"File has no extractable text"** - Upload a file with readable text content
4. **"Authentication failed"** - Verify Supabase JWT token is valid

### Debug Steps

1. Test with `/test-ai-quiz` endpoint first
2. Check server logs for detailed error messages
3. Verify file exists and has text content
4. Ensure user has proper authentication token
5. Check database connection and RLS policies

## Integration Notes

- Quiz generation is **asynchronous** and may take 10-30 seconds
- **Caching is automatic** - subsequent calls return cached results
- **Delete endpoint** allows forcing regeneration of quizzes
- **Test endpoints** available for development and debugging
