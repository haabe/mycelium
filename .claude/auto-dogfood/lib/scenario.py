"""Scenario loading and validation."""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


@dataclass
class PlantedFailure:
    type: str
    trigger: str
    description: str
    personas_rejecting: list[str] = field(default_factory=list)
    secret_content: str = ""
    skip_target: str = ""


@dataclass
class JourneyStep:
    skill: str
    rounds: int = 1
    expect_blocked: bool = False
    planted_failure: str | None = None


@dataclass
class Scenario:
    name: str
    product_name: str
    product_type: str
    product_description: str
    product_pitch: str
    persona_name: str
    persona_role: str
    persona_style: str
    persona_knowledge: str
    persona_answers: dict[str, str]
    project_type: str
    dogfood: bool
    planted_failures: list[PlantedFailure]
    journey: list[JourneyStep]
    success_criteria: list[dict[str, Any]]
    max_rounds: int
    max_time_seconds: int
    model_mycelium: str
    model_user: str
    difficulty: str = "medium"
    initial_state: dict[str, str] = field(default_factory=dict)

    @classmethod
    def load(cls, path: str | Path) -> "Scenario":
        with open(path) as f:
            data = yaml.safe_load(f)

        product = data.get("product", {})
        persona = data.get("persona", {})
        budget = data.get("budget", {})
        models = budget.get("model_overrides", {})

        failures = [
            PlantedFailure(
                type=pf["type"],
                trigger=pf["trigger"],
                description=pf.get("description", ""),
                personas_rejecting=pf.get("personas_rejecting", []),
                secret_content=pf.get("secret_content", ""),
                skip_target=pf.get("skip_target", ""),
            )
            for pf in data.get("planted_failures", [])
        ]

        journey = [
            JourneyStep(
                skill=step["skill"],
                rounds=step.get("rounds", 1),
                expect_blocked=step.get("expect_blocked", False),
                planted_failure=step.get("planted_failure"),
            )
            for step in data.get("journey", [])
        ]

        return cls(
            name=data["name"],
            product_name=product["name"],
            product_type=product["type"],
            product_description=product.get("description", ""),
            product_pitch=product.get("pitch", ""),
            persona_name=persona.get("name", "Alex"),
            persona_role=persona.get("role", "Developer"),
            persona_style=persona.get("style", "Pragmatic"),
            persona_knowledge=persona.get("knowledge", ""),
            persona_answers=persona.get("answers", {}),
            project_type=data.get("project_type", "solo_product"),
            dogfood=data.get("dogfood", True),
            planted_failures=failures,
            journey=journey,
            success_criteria=data.get("success_criteria", []),
            max_rounds=budget.get("max_rounds", 12),
            max_time_seconds=budget.get("max_time_seconds", 600),
            model_mycelium=models.get("mycelium_agent", "sonnet"),
            model_user=models.get("user_simulator", "haiku"),
            difficulty=data.get("difficulty", "medium"),
            initial_state=data.get("initial_state", {}),
        )

    def get_failure_for_skill(self, skill: str) -> PlantedFailure | None:
        for pf in self.planted_failures:
            if pf.trigger == skill:
                return pf
        return None
