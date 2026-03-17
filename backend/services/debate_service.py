# Debate logic is handled inside analysis_service.py -> debate_documents()
# This file exists for structural completeness
from services.analysis_service import analysis_service

def debate(text1, text2, name1, name2):
    return analysis_service.debate_documents(text1, text2, name1, name2)
