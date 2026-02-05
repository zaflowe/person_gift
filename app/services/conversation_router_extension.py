
class ConversationStateResponse(BaseModel):
    conversation_id: str
    messages: List[dict]
    stage: str
    intent: Optional[str]

@router.get("/current", response_model=ConversationStateResponse)
async def get_current_conversation(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get the persistent conversation state."""
    # Find the most recent session
    session = db.query(ConversationSession).filter(
        ConversationSession.user_id == current_user.id
    ).order_by(ConversationSession.created_at.desc()).first()
    
    if not session:
        # Create initial session if none exists
        session = ConversationSession(
            id=str(uuid.uuid4()),
            user_id=current_user.id,
            stage="intent",
            messages="[]",
            collected_info="{}"
        )
        db.add(session)
        db.commit()
    
    messages = json.loads(session.messages) if session.messages else []
    
    return ConversationStateResponse(
        conversation_id=session.id,
        messages=messages,
        stage=session.stage,
        intent=session.intent
    )

@router.post("/reset", response_model=ConversationStateResponse)
async def reset_conversation(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Force start a new conversation thread."""
    # Create new session immediately
    session = ConversationSession(
        id=str(uuid.uuid4()),
        user_id=current_user.id,
        stage="intent",
        messages="[]",
        collected_info="{}"
    )
    db.add(session)
    db.commit()
    
    return ConversationStateResponse(
        conversation_id=session.id,
        messages=[],
        stage="intent",
        intent=None
    )
