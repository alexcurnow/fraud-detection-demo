"""Ollama LLM client for generating fraud explanations."""

import os
import logging
import httpx
from typing import Dict, Any, Optional, List

logger = logging.getLogger(__name__)


class OllamaClient:
    """
    Client for Ollama LLM API.

    Generates natural language explanations of fraud detections.
    """

    def __init__(self):
        self.base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        self.model = os.getenv("OLLAMA_MODEL", "llama3.2")
        self.timeout = 120.0  # 2 minutes for LLM generation

    def _is_available(self) -> bool:
        """Check if Ollama service is available."""
        try:
            with httpx.Client(timeout=5.0) as client:
                response = client.get(f"{self.base_url}/api/tags")
                return response.status_code == 200
        except Exception as e:
            logger.warning(f"Ollama not available: {e}")
            return False

    def _ensure_model_loaded(self):
        """Ensure the model is pulled/loaded."""
        try:
            with httpx.Client(timeout=300.0) as client:  # 5 min for model pull
                response = client.post(
                    f"{self.base_url}/api/pull",
                    json={"name": self.model}
                )
                if response.status_code == 200:
                    logger.info(f"Model {self.model} is ready")
                else:
                    logger.warning(f"Failed to pull model: {response.text}")
        except Exception as e:
            logger.error(f"Error ensuring model loaded: {e}")

    def generate(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        """
        Generate text from prompt using Ollama.

        Args:
            prompt: User prompt
            system_prompt: Optional system prompt for context

        Returns:
            Generated text
        """
        if not self._is_available():
            return "LLM service is currently unavailable. Please check Ollama container status."

        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": 0.7,
                "top_p": 0.9,
                "num_predict": 150  # Shorter responses for faster CPU inference
            }
        }

        if system_prompt:
            payload["system"] = system_prompt

        try:
            with httpx.Client(timeout=self.timeout) as client:
                response = client.post(
                    f"{self.base_url}/api/generate",
                    json=payload
                )

                if response.status_code == 200:
                    result = response.json()
                    return result.get("response", "")
                else:
                    logger.error(f"Ollama API error: {response.status_code} - {response.text}")
                    return f"Error generating explanation: {response.status_code}"

        except httpx.TimeoutException:
            logger.error("LLM generation timed out")
            return "Explanation generation timed out. Please try again."
        except Exception as e:
            logger.error(f"Error calling Ollama API: {e}")
            return f"Error generating explanation: {str(e)}"

    def explain_transaction_fraud(
        self,
        transaction_data: Dict[str, Any],
        user_context: Dict[str, Any],
        fraud_analysis: Dict[str, Any]
    ) -> str:
        """
        Generate natural language explanation for a flagged transaction.

        Args:
            transaction_data: Transaction details
            user_context: User history and patterns
            fraud_analysis: ML model results and flagged reasons

        Returns:
            Human-readable fraud explanation
        """
        system_prompt = """You are a fraud detection analyst. Explain fraud alerts in clear,
professional language for non-technical fraud investigators. Focus on:
1. Why the transaction was flagged
2. Key suspicious indicators
3. Recommended action

Keep explanations concise (2-3 paragraphs). Be specific with details."""

        prompt = f"""Explain this fraud alert to a fraud investigator:

TRANSACTION:
- Amount: ${transaction_data.get('amount', 0):.2f}
- Merchant: {transaction_data.get('merchant_name', 'Unknown')} ({transaction_data.get('merchant_category', 'N/A')})
- Location: Lat {transaction_data.get('latitude', 'N/A')}, Long {transaction_data.get('longitude', 'N/A')}
- Time: {transaction_data.get('timestamp', 'Unknown')}

USER CONTEXT:
- Average transaction amount: ${user_context.get('avg_transaction_amount', 0):.2f}
- Total transactions: {user_context.get('total_transactions', 0)}
- Common merchants: {', '.join(user_context.get('common_merchants', []))}
- Typical hours: {', '.join(map(str, user_context.get('typical_hours', [])))}
- Fraud flags: {user_context.get('fraud_flags', 0)}

FRAUD ANALYSIS:
- Risk Score: {fraud_analysis.get('risk_score', 0):.1%}
- Flagged Reasons: {', '.join(fraud_analysis.get('flagged_reasons', []))}

Provide a clear explanation of why this transaction is suspicious and what action should be taken."""

        return self.generate(prompt, system_prompt)

    def explain_fraud_ring(
        self,
        ring_type: str,
        ring_data: Dict[str, Any]
    ) -> str:
        """
        Generate natural language explanation for a detected fraud ring.

        Args:
            ring_type: Type of fraud ring (device_sharing, money_mule, etc.)
            ring_data: Ring detection data

        Returns:
            Human-readable fraud ring explanation
        """
        system_prompt = """You are a fraud detection analyst specializing in organized fraud rings.
Explain network fraud patterns clearly for fraud investigators. Focus on:
1. What pattern was detected
2. Why it's suspicious
3. Risk level and recommended action

Use professional but accessible language."""

        # Build context based on ring type
        if ring_type == "device_sharing":
            context = f"""
DEVICE SHARING RING DETECTED:
- Device ID: {ring_data.get('device_id', 'Unknown')}
- Accounts involved: {ring_data.get('account_count', 0)} accounts
- Accounts: {', '.join(ring_data.get('accounts', [])[:5])}
- Total transactions: {ring_data.get('transaction_count', 0)}
"""
        elif ring_type == "money_mule":
            context = f"""
MONEY MULE CHAIN DETECTED:
- Chain length: {ring_data.get('hops', 0)} transfers
- Accounts in chain: {' → '.join(ring_data.get('chain', []))}
- Total amount transferred: ${ring_data.get('total_amount', 0):.2f}
- Time span: {ring_data.get('first_transfer', 'Unknown')} to {ring_data.get('last_transfer', 'Unknown')}
"""
        elif ring_type == "merchant_collusion":
            context = f"""
MERCHANT COLLUSION DETECTED:
- Merchant: {ring_data.get('merchant_name', 'Unknown')} ({ring_data.get('merchant_category', 'N/A')})
- Users involved: {ring_data.get('user_count', 0)} accounts
- Total transactions: {ring_data.get('transaction_count', 0)}
- Total amount: ${ring_data.get('total_amount', 0):.2f}
"""
        else:
            context = f"""
FRAUD RING DETECTED ({ring_type.upper()}):
- Accounts involved: {ring_data.get('account_count', 0)}
- Pattern details: {str(ring_data)}
"""

        prompt = f"""{context}

Explain this fraud ring detection to an investigator. What makes this pattern suspicious?
What's the likely fraud scheme? What action should be taken?"""

        return self.generate(prompt, system_prompt)

    def generate_executive_summary(
        self,
        flagged_transactions: List[Dict[str, Any]],
        detected_rings: Dict[str, List[Dict[str, Any]]]
    ) -> str:
        """
        Generate executive summary of fraud activity.

        Args:
            flagged_transactions: List of flagged transactions
            detected_rings: Detected fraud rings by type

        Returns:
            Executive summary report
        """
        system_prompt = """You are a senior fraud analyst creating an executive summary.
Provide a high-level overview of fraud activity for management. Focus on:
1. Overall fraud landscape
2. Key patterns and trends
3. Priority actions

Be concise and strategic."""

        total_rings = sum(len(rings) for rings in detected_rings.values())

        prompt = f"""Generate an executive summary of current fraud activity:

ISOLATED FRAUD:
- Flagged transactions: {len(flagged_transactions)}
- Total risk exposure: ${sum(t.get('amount', 0) for t in flagged_transactions):.2f}

ORGANIZED FRAUD RINGS:
- Total rings detected: {total_rings}
- Device sharing rings: {len(detected_rings.get('device_sharing', []))}
- Money mule chains: {len(detected_rings.get('money_mule', []))}
- Merchant collusion: {len(detected_rings.get('merchant_collusion', []))}
- Account takeover clusters: {len(detected_rings.get('account_takeover', []))}
- Synthetic identity rings: {len(detected_rings.get('synthetic_identity', []))}

Provide a 3-4 paragraph executive summary highlighting key risks and recommended priorities."""

        return self.generate(prompt, system_prompt)
