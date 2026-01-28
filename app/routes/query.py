"""
Main query routes for Saathi API - Fully AI-Powered
"""
from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from typing import Optional
from pydantic import BaseModel

from app.services.groq_service import groq_service
from app.services.groq_llm_service import groq_llm_service as gemini_service
from app.services.openai_vision_service import openai_vision_service
from app.services.search_service import search_service
from app.utils.image_utils import process_screenshot

router = APIRouter()


class QueryResponse(BaseModel):
    """Response model for queries"""
    success: bool
    query: str
    response: str
    has_screen_context: bool
    used_web_search: bool
    error: Optional[str] = None


class TranscriptionResponse(BaseModel):
    """Response model for transcription"""
    success: bool
    text: Optional[str]
    error: Optional[str] = None


@router.post("/query", response_model=QueryResponse)
async def process_query(
    audio: Optional[UploadFile] = File(None),
    image: Optional[UploadFile] = File(None),
    text: Optional[str] = Form(None)
):
    """
    Main endpoint for Saathi queries - Fully AI-powered decision making
    
    Accepts:
    - audio: Audio file (optional) - will be transcribed to text
    - image: Screenshot (optional) - will be analyzed for context
    - text: Direct text query (optional) - used if no audio provided
    
    Returns:
    - Intelligent AI response based on query and context
    """
    
    # ============================================================================
    # STEP 1: Get query text (from audio or direct text)
    # ============================================================================
    query_text = None
    
    if audio:
        print(f"[DEBUG] Audio received: {audio.filename}")
        audio_bytes = await audio.read()
        print(f"[DEBUG] Audio bytes read: {len(audio_bytes)} bytes")
        
        transcription_result = await groq_service.transcribe_audio(
            audio_bytes, 
            audio.filename or "audio.wav"
        )
        
        if not transcription_result["success"]:
            raise HTTPException(
                status_code=400,
                detail=f"Audio transcription failed: {transcription_result.get('error', 'Unknown error')}"
            )
        
        query_text = transcription_result["text"]
        print(f"[INFO] Transcribed: '{query_text}'")
    
    elif text:
        query_text = text
        print(f"[INFO] Text query: '{query_text}'")
    
    else:
        raise HTTPException(
            status_code=400,
            detail="Either 'audio' or 'text' parameter is required"
        )
    
    # ============================================================================
    # STEP 2: AI-powered screenshot analysis with intelligent recommendations
    # ============================================================================
    screen_analysis = None
    has_screen = False
    ai_structured_data = None
    
    if image:
        print(f"[DEBUG] Image received: {image.filename}, size: {image.size if hasattr(image, 'size') else 'unknown'}")
        image_bytes = await image.read()
        print(f"[DEBUG] Image bytes read: {len(image_bytes)} bytes")
        
        processed_image, error = process_screenshot(image_bytes)
        print(f"[DEBUG] Image processed: error={error}")
        
        if error:
            raise HTTPException(status_code=400, detail=error)
        
        # Let AI analyze and decide everything
        print("[INFO] Asking AI to analyze screenshot...")
        analysis_result = await openai_vision_service.analyze_screen_with_query(
            processed_image,
            query_text
        )
        
        if analysis_result["success"]:
            screen_analysis = analysis_result["analysis"]
            ai_structured_data = analysis_result.get("structured_data")
            has_screen = True
            
            print(f"[AI ANALYSIS] {screen_analysis[:100]}...")
            
            if ai_structured_data:
                print(f"[AI DECISION] Brand/Product: {ai_structured_data.get('brand_name', 'None')}")
                print(f"[AI DECISION] Needs Research: {ai_structured_data.get('needs_web_research', False)}")
                if ai_structured_data.get("why_research"):
                    print(f"[AI REASONING] {ai_structured_data['why_research']}")
        else:
            print(f"[WARNING] Screen analysis failed: {analysis_result.get('error')}")
            screen_analysis = None
    
    # ============================================================================
    # STEP 3: AI-powered web search decision (no hard-coded rules!)
    # ============================================================================
    search_results = None
    used_search = False
    
    # Check if AI recommends web research
    ai_wants_research = False
    ai_search_query = None
    
    if ai_structured_data:
        ai_wants_research = ai_structured_data.get("needs_web_research", False)
        ai_search_query = ai_structured_data.get("search_query")
    
    # Also check if query itself indicates need for information
    # (Simple fallback if no image provided)
    query_indicators = [
        "tell me about", "what is", "who is", "should i", "is it",
        "authentic", "real", "fake", "review", "price", "buy"
    ]
    query_wants_info = any(indicator in query_text.lower() for indicator in query_indicators)
    
    # Trigger search if AI recommends OR query clearly asks for info
    needs_search = ai_wants_research or query_wants_info
    
    if needs_search:
        print("[INFO] 🔍 Triggering web search")
        print(f"  → AI recommendation: {ai_wants_research}")
        print(f"  → Query needs info: {query_wants_info}")
        
        # Use AI's suggested search query if available, otherwise use user's query
        if ai_search_query:
            search_query = ai_search_query
            print(f"  → Using AI's search query: '{search_query}'")
        else:
            search_query = query_text
            print(f"  → Using user's query: '{search_query}'")
        
        # Perform web search
        search_result = await search_service.search(search_query, num_results=5)
        
        if search_result["success"] and search_result["results"]:
            search_results = search_result["results"]
            used_search = True
            print(f"[INFO] ✅ Found {len(search_results)} search results")
            
            # Log top result for debugging
            if search_results:
                top_result = search_results[0]
                print(f"  → Top result: {top_result['title'][:60]}...")
        else:
            print(f"[WARNING] ⚠️ Search returned no results")
    else:
        print("[INFO] ℹ️ No web search needed (AI decision)")
    
    # ============================================================================
    # STEP 4: Generate final intelligent response with all context
    # ============================================================================
    
    # Format search results with clear instructions for AI
    search_context = None
    if search_results:
        search_context = "🔍 WEB SEARCH RESULTS (Use this to answer directly - don't ask user to search!):\n\n"
        
        for i, result in enumerate(search_results[:5], 1):
            search_context += f"{i}. {result['title']}\n"
            search_context += f"   Source: {result['source']}\n"
            search_context += f"   Info: {result['snippet']}\n\n"
        
        print(f"[DEBUG] Prepared search context with {len(search_results)} results")
    
    # Add structured data insights if available
    context_enrichment = ""
    if ai_structured_data:
        if ai_structured_data.get("brand_name"):
            context_enrichment += f"\n📦 Brand/Product Detected: {ai_structured_data['brand_name']}"
        if ai_structured_data.get("price_shown"):
            context_enrichment += f"\n💰 Price Shown: {ai_structured_data['price_shown']}"
    
    # Combine all context
    full_context = screen_analysis
    if context_enrichment:
        full_context = (full_context or "") + context_enrichment
    
    print("[INFO] 🤖 Generating final response with Groq LLM...")
    final_response = await gemini_service.generate_response(
        query=query_text,
        context=full_context,
        search_results=search_context
    )
    
    if not final_response["success"]:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate response: {final_response.get('error', 'Unknown error')}"
        )
    
    print("[SUCCESS] ✅ Query processed successfully")
    print(f"[RESPONSE] {final_response['response'][:100]}...")
    
    return QueryResponse(
        success=True,
        query=query_text,
        response=final_response["response"],
        has_screen_context=has_screen,
        used_web_search=used_search,
        error=None
    )


@router.post("/transcribe", response_model=TranscriptionResponse)
async def transcribe_audio(audio: UploadFile = File(...)):
    """
    Standalone endpoint for speech-to-text
    
    Accepts:
    - audio: Audio file
    
    Returns:
    - Transcribed text
    """
    audio_bytes = await audio.read()
    result = await groq_service.transcribe_audio(
        audio_bytes,
        audio.filename or "audio.wav"
    )
    
    if not result["success"]:
        raise HTTPException(
            status_code=400,
            detail=f"Transcription failed: {result.get('error', 'Unknown error')}"
        )
    
    return TranscriptionResponse(
        success=True,
        text=result["text"],
        error=None
    )


@router.post("/analyze-screen")
async def analyze_screen(image: UploadFile = File(...)):
    """
    Analyze screenshot without specific query
    
    Accepts:
    - image: Screenshot
    
    Returns:
    - Basic description of what's on screen
    """
    image_bytes = await image.read()
    processed_image, error = process_screenshot(image_bytes)
    
    if error:
        raise HTTPException(status_code=400, detail=error)
    
    result = await openai_vision_service.analyze_screen_only(processed_image)
    
    if not result["success"]:
        raise HTTPException(
            status_code=500,
            detail=f"Screen analysis failed: {result.get('error', 'Unknown error')}"
        )
    
    return {
        "success": True,
        "description": result["description"]
    }