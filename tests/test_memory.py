"""
Unit tests for AgentMemory episodic/semantic storage and retrieval.
"""

import pytest

from src.agents.super_agentic_agents import AgentMemory


class TestAgentMemoryEpisodic:
    """Tests for episodic (short-term) memory operations."""

    def test_store_episode_single_entry(self):
        memory = AgentMemory(agent_id="agent-1")
        memory.store_episode("key1", "value1")
        assert memory.retrieve("key1", "episodic") == "value1"

    def test_store_episode_overwrites_same_key(self):
        memory = AgentMemory(agent_id="agent-1")
        memory.store_episode("key1", "first")
        memory.store_episode("key1", "second")
        assert memory.retrieve("key1", "episodic") == "second"

    def test_retrieve_missing_key_returns_none(self):
        memory = AgentMemory(agent_id="agent-1")
        assert memory.retrieve("nonexistent", "episodic") is None

    def test_store_episode_complex_value(self):
        memory = AgentMemory(agent_id="agent-1")
        payload = {"nested": {"list": [1, 2, 3]}, "flag": True}
        memory.store_episode("complex", payload)
        assert memory.retrieve("complex", "episodic") == payload

    def test_fifo_eviction_oldest_entry_removed(self):
        memory = AgentMemory(agent_id="agent-1", max_episodes=3)
        memory.store_episode("k1", "v1")
        memory.store_episode("k2", "v2")
        memory.store_episode("k3", "v3")
        # Adding a 4th entry should evict k1
        memory.store_episode("k4", "v4")
        assert memory.retrieve("k1", "episodic") is None
        assert memory.retrieve("k2", "episodic") == "v2"
        assert memory.retrieve("k3", "episodic") == "v3"
        assert memory.retrieve("k4", "episodic") == "v4"

    def test_fifo_eviction_preserves_capacity(self):
        memory = AgentMemory(agent_id="agent-1", max_episodes=2)
        for i in range(10):
            memory.store_episode(f"k{i}", f"v{i}")
        assert len(memory.episodic_memory) == 2

    def test_fifo_eviction_sequential_ordering(self):
        memory = AgentMemory(agent_id="agent-1", max_episodes=2)
        memory.store_episode("k1", "v1")
        memory.store_episode("k2", "v2")
        memory.store_episode("k3", "v3")  # evicts k1
        memory.store_episode("k4", "v4")  # evicts k2
        assert memory.retrieve("k1", "episodic") is None
        assert memory.retrieve("k2", "episodic") is None
        assert memory.retrieve("k3", "episodic") == "v3"
        assert memory.retrieve("k4", "episodic") == "v4"

    def test_episodic_memory_not_visible_as_semantic(self):
        memory = AgentMemory(agent_id="agent-1")
        memory.store_episode("key1", "value1")
        assert memory.retrieve("key1", "semantic") is None


class TestAgentMemorySemantic:
    """Tests for semantic (long-term) memory operations."""

    def test_store_semantic_single_entry(self):
        memory = AgentMemory(agent_id="agent-1")
        memory.store_semantic("fact1", "the sky is blue")
        assert memory.retrieve("fact1", "semantic") == "the sky is blue"

    def test_store_semantic_complex_value(self):
        memory = AgentMemory(agent_id="agent-1")
        knowledge = {"domain": "physics", "formula": "E=mc^2"}
        memory.store_semantic("physics", knowledge)
        assert memory.retrieve("physics", "semantic") == knowledge

    def test_retrieve_missing_semantic_key_returns_none(self):
        memory = AgentMemory(agent_id="agent-1")
        assert memory.retrieve("absent", "semantic") is None

    def test_semantic_access_count_starts_at_zero(self):
        memory = AgentMemory(agent_id="agent-1")
        memory.store_semantic("fact1", "value")
        assert memory.semantic_memory["fact1"]["access_count"] == 0

    def test_semantic_access_count_increments_on_retrieve(self):
        memory = AgentMemory(agent_id="agent-1")
        memory.store_semantic("fact1", "value")
        memory.retrieve("fact1", "semantic")
        assert memory.semantic_memory["fact1"]["access_count"] == 1

    def test_semantic_access_count_increments_multiple_times(self):
        memory = AgentMemory(agent_id="agent-1")
        memory.store_semantic("fact1", "value")
        memory.retrieve("fact1", "semantic")
        memory.retrieve("fact1", "semantic")
        memory.retrieve("fact1", "semantic")
        assert memory.semantic_memory["fact1"]["access_count"] == 3

    def test_semantic_not_visible_as_episodic(self):
        memory = AgentMemory(agent_id="agent-1")
        memory.store_semantic("key1", "value1")
        assert memory.retrieve("key1", "episodic") is None

    def test_store_semantic_overwrites_same_key(self):
        memory = AgentMemory(agent_id="agent-1")
        memory.store_semantic("key1", "old")
        memory.store_semantic("key1", "new")
        assert memory.retrieve("key1", "semantic") == "new"


class TestAgentMemoryAutoRetrieval:
    """Tests for auto-mode memory retrieval (episodic first, then semantic)."""

    def test_auto_retrieves_from_episodic_first(self):
        memory = AgentMemory(agent_id="agent-1")
        memory.store_episode("shared", "episodic_value")
        memory.store_semantic("shared", "semantic_value")
        assert memory.retrieve("shared", "auto") == "episodic_value"

    def test_auto_falls_back_to_semantic(self):
        memory = AgentMemory(agent_id="agent-1")
        memory.store_semantic("fact", "semantic_value")
        assert memory.retrieve("fact", "auto") == "semantic_value"

    def test_auto_returns_none_when_both_absent(self):
        memory = AgentMemory(agent_id="agent-1")
        assert memory.retrieve("missing", "auto") is None

    def test_default_memory_type_is_auto(self):
        memory = AgentMemory(agent_id="agent-1")
        memory.store_semantic("key", "val")
        assert memory.retrieve("key") == "val"
