from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Sequence


class GhostMode(str, Enum):
    NORMAL = "normal"
    SECURITY = "security"


@dataclass
class ThreatRule:
    name: str
    keywords: Sequence[str]
    weight: int = 1


@dataclass
class GhostModalState:
    mode: GhostMode = GhostMode.NORMAL
    threat_score: int = 0
    threshold: int = 3
    reasons: List[str] = field(default_factory=list)
    last_evaluated_at: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "mode": self.mode.value,
            "threat_score": self.threat_score,
            "threshold": self.threshold,
            "reasons": list(self.reasons),
            "last_evaluated_at": self.last_evaluated_at,
        }


class GhostModal:
    """Adaptive modal router for AI and cybersecurity toolboxes.

    - Normal mode: general AI tools
    - Security mode: defensive cyber tools
    """

    def __init__(
        self,
        agent_name: str,
        threshold: int = 3,
        threat_rules: Optional[Sequence[ThreatRule]] = None,
    ) -> None:
        self.agent_name = agent_name
        self.state = GhostModalState(threshold=threshold)
        self._audit_log: List[Dict[str, Any]] = []

        self.normal_tools: Dict[str, Callable[..., Any]] = {
            "summarize": self._tool_summarize,
            "plan": self._tool_plan,
            "refactor_hint": self._tool_refactor_hint,
        }

        self.security_tools: Dict[str, Callable[..., Any]] = {
            "threat_scan": self._tool_threat_scan,
            "ioc_extract": self._tool_ioc_extract,
            "incident_note": self._tool_incident_note,
        }

        self.threat_rules: List[ThreatRule] = list(threat_rules or self._default_rules())

    def evaluate(self, text: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        context = context or {}
        lowered = text.lower()

        score = 0
        reasons: List[str] = []
        for rule in self.threat_rules:
            if any(k in lowered for k in rule.keywords):
                score += rule.weight
                reasons.append(rule.name)

        mode = GhostMode.SECURITY if score >= self.state.threshold else GhostMode.NORMAL

        now = datetime.now(timezone.utc).isoformat()
        self.state.mode = mode
        self.state.threat_score = score
        self.state.reasons = reasons
        self.state.last_evaluated_at = now

        self._audit_log.append(
            {
                "timestamp": now,
                "agent": self.agent_name,
                "mode": mode.value,
                "threat_score": score,
                "threshold": self.state.threshold,
                "reasons": reasons,
                "context": context,
            }
        )

        return self.state.to_dict()

    def execute(self, tool_name: str, *args: Any, **kwargs: Any) -> Any:
        tools = self._active_tools()
        if tool_name not in tools:
            allowed = ", ".join(sorted(tools.keys()))
            raise ValueError(
                f"Tool '{tool_name}' is not available in mode '{self.state.mode.value}'. "
                f"Allowed tools: {allowed}"
            )

        result = tools[tool_name](*args, **kwargs)
        self._audit_log.append(
            {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "agent": self.agent_name,
                "event": "tool_execution",
                "mode": self.state.mode.value,
                "tool": tool_name,
            }
        )
        return result

    def register_tool(self, mode: GhostMode, name: str, fn: Callable[..., Any]) -> None:
        if mode == GhostMode.NORMAL:
            self.normal_tools[name] = fn
        else:
            self.security_tools[name] = fn

    def get_state(self) -> Dict[str, Any]:
        return self.state.to_dict()

    def get_audit_log(self) -> List[Dict[str, Any]]:
        return list(self._audit_log)

    def _active_tools(self) -> Dict[str, Callable[..., Any]]:
        return self.security_tools if self.state.mode == GhostMode.SECURITY else self.normal_tools

    @staticmethod
    def _default_rules() -> List[ThreatRule]:
        return [
            ThreatRule("malware_indicator", ["malware", "ransomware", "worm", "trojan"], 2),
            ThreatRule("exploit_indicator", ["exploit", "zero-day", "payload", "backdoor"], 2),
            ThreatRule("credential_risk", ["credential", "password", "token", "api key", "secret"], 2),
            ThreatRule("injection_risk", ["sql injection", "xss", "command injection"], 2),
            ThreatRule("exfiltration_risk", ["exfiltrate", "data leak", "privilege escalation"], 2),
        ]

    # ------------------------------
    # Built-in normal tools
    # ------------------------------
    def _tool_summarize(self, text: str) -> Dict[str, Any]:
        return {
            "tool": "summarize",
            "summary": text[:200] + ("..." if len(text) > 200 else ""),
        }

    def _tool_plan(self, objective: str) -> Dict[str, Any]:
        return {
            "tool": "plan",
            "steps": [
                f"Define objective: {objective}",
                "Identify constraints",
                "Draft minimal action sequence",
                "Validate outcome",
            ],
        }

    def _tool_refactor_hint(self, code_smell: str) -> Dict[str, Any]:
        return {
            "tool": "refactor_hint",
            "hint": f"Address '{code_smell}' with smaller functions and safer abstractions.",
        }

    # ------------------------------
    # Built-in security tools
    # ------------------------------
    def _tool_threat_scan(self, text: str) -> Dict[str, Any]:
        state = self.evaluate(text)
        return {
            "tool": "threat_scan",
            "mode": state["mode"],
            "threat_score": state["threat_score"],
            "reasons": state["reasons"],
        }

    def _tool_ioc_extract(self, text: str) -> Dict[str, Any]:
        indicators = []
        for token in text.split():
            if any(token.lower().endswith(sfx) for sfx in (".exe", ".dll", ".bat", ".ps1")):
                indicators.append({"type": "file", "value": token.strip()})
            if token.count(".") >= 3 and all(part.isdigit() for part in token.split(".") if part):
                indicators.append({"type": "ip", "value": token.strip()})
        return {"tool": "ioc_extract", "indicators": indicators}

    def _tool_incident_note(self, finding: str) -> Dict[str, Any]:
        return {
            "tool": "incident_note",
            "agent": self.agent_name,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "finding": finding,
            "recommended_actions": [
                "Isolate affected component",
                "Rotate exposed credentials",
                "Collect forensic artifacts",
                "Open incident ticket and escalate",
            ],
        }
