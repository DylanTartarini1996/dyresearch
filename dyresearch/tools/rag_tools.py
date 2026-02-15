## NOTE: THIS IS JUST A MOCK FOR NOW

def rag(query: str) -> dict:
    """
    Performs Retrieval Augmented Generation based on vector similarity to give answer to the user's query.

    
    --------
    Returns:
    --------
    `dict`: A dictionary containing the answer information.
            Includes a 'status' key ('success' or 'error').
            If 'success', includes a 'answer' key with the answer to the query.
            If 'error', includes an 'error_message' key.
    """
    if "AI" in query:
        return {"status": "success", "answer": f"This question {query} is on AI"}
    else:
        return {"status": "error", "error_message": f"This question {query} is NOT on AI"}