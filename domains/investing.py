import datetime
import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional
from core.memory.manager import MemoryManager

logger = logging.getLogger("mithrandir")

class InvestingDomain:
    """Domain module handling the Confluence Framework for investing decisions.
    
    Combines Macro, Sentiment, and Technical indicators to output a final Confluence Score (1-10)
    with a text justification, saving results to SQLite.
    """
    def __init__(self, db_path: Optional[Path] = None):
        self.manager = MemoryManager(db_path)

    def calculate_confluence(
        self,
        tom_lee_stance: float,
        cpi_liquidity: float,
        etf_flows: float,
        fintwit_velocity: float,
        cnbc_amplitude: float,
        skeptic_flow: float,
        sr_alignment: float,
        momentum_slope: float,
        volume_divergence: float,
    ) -> Dict[str, Any]:
        """Calculates section averages, final Confluence Score, and returns recommendation and justification."""
        
        # Validations
        inputs = {
            "Tom Lee pivot stance": tom_lee_stance,
            "CPI/liquidity trend": cpi_liquidity,
            "ETF flows": etf_flows,
            "FinTwit velocity": fintwit_velocity,
            "CNBC amplitude": cnbc_amplitude,
            "Skeptic flow": skeptic_flow,
            "S/R alignment": sr_alignment,
            "Momentum slope": momentum_slope,
            "Volume divergence": volume_divergence,
        }
        for name, val in inputs.items():
            if not (1.0 <= val <= 10.0):
                raise ValueError(f"{name} rating must be between 1.0 and 10.0. Got: {val}")

        macro_score = (tom_lee_stance + cpi_liquidity + etf_flows) / 3.0
        sentiment_score = (fintwit_velocity + cnbc_amplitude + skeptic_flow) / 3.0
        technical_score = (sr_alignment + momentum_slope + volume_divergence) / 3.0
        
        final_score = (macro_score + sentiment_score + technical_score) / 3.0
        
        # Generate Recommendation
        if final_score >= 7.5:
            recommendation = "Buy strength"
        elif 5.5 <= final_score < 7.5:
            recommendation = "Wait"
        elif 3.5 <= final_score < 5.5:
            recommendation = "Buy silence"
        else:
            recommendation = "Trim strength"

        # Generate Justification Text
        macro_desc = "bullish" if macro_score >= 7.0 else "neutral" if macro_score >= 4.0 else "bearish"
        sent_desc = "euphoric" if sentiment_score >= 7.0 else "moderate" if sentiment_score >= 4.0 else "depressed"
        tech_desc = "strong" if technical_score >= 7.0 else "consolidating" if technical_score >= 4.0 else "weak"
        
        justification = (
            f"Mithrandir 2.0 Confluence Score is {final_score:.2f} / 10.0 (Recommendation: {recommendation}).\n"
            f"Macro Section ({macro_score:.2f}/10): Currently {macro_desc}. "
            f"[Tom Lee: {tom_lee_stance}, CPI/Liquidity: {cpi_liquidity}, ETF Flows: {etf_flows}]\n"
            f"Sentiment Section ({sentiment_score:.2f}/10): Currently {sent_desc}. "
            f"[FinTwit: {fintwit_velocity}, CNBC: {cnbc_amplitude}, Skeptics: {skeptic_flow}]\n"
            f"Technical Section ({technical_score:.2f}/10): Currently {tech_desc}. "
            f"[S/R: {sr_alignment}, Momentum: {momentum_slope}, Volume Divergence: {volume_divergence}]\n"
            f"Justification: The framework aligns at a '{recommendation}' recommendation. "
            f"Technicals are {tech_desc} while Macro posture indicates {macro_desc} conditions, "
            f"and crowd sentiment is {sent_desc}."
        )

        return {
            "macro_score": macro_score,
            "sentiment_score": sentiment_score,
            "technical_score": technical_score,
            "final_score": final_score,
            "recommendation": recommendation,
            "justification": justification,
            "ratings": {
                "tom_lee_stance": tom_lee_stance,
                "cpi_liquidity": cpi_liquidity,
                "etf_flows": etf_flows,
                "fintwit_velocity": fintwit_velocity,
                "cnbc_amplitude": cnbc_amplitude,
                "skeptic_flow": skeptic_flow,
                "sr_alignment": sr_alignment,
                "momentum_slope": momentum_slope,
                "volume_divergence": volume_divergence,
            }
        }

    def save_confluence_report(self, report: Dict[str, Any]) -> int:
        """Saves calculated confluence report into SQLite memory."""
        content = report["justification"]
        metadata = {
            "ratings": report["ratings"],
            "macro_score": report["macro_score"],
            "sentiment_score": report["sentiment_score"],
            "technical_score": report["technical_score"],
            "final_score": report["final_score"],
            "recommendation": report["recommendation"],
            "date": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        
        memory_id = self.manager.add_memory(
            category="investing",
            content=content,
            metadata=metadata
        )
        logger.info(f"Confluence report stored under investing with memory ID {memory_id}.")
        return memory_id

    def list_confluence_reports(self) -> List[Dict[str, Any]]:
        """Lists all past confluence reports chronologically."""
        return self.manager.search_memories(category="investing")
