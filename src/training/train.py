"""
Training utilities for the AI-morphasis learning models.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np

from src.models.neural_network import AgentLearningModel, ExperienceReplay


class TrainingEnvironment:
    """Small synthetic environment for exercising the training loop."""

    def __init__(
        self,
        state_size: int,
        action_size: int,
        max_steps: int = 500,
        reward_scale: float = 1.0,
    ) -> None:
        self.state_size = state_size
        self.action_size = action_size
        self.max_steps = max_steps
        self.reward_scale = reward_scale
        self.current_step = 0
        self._state = np.zeros(self.state_size, dtype=np.float32)

    def reset(self) -> np.ndarray:
        """Reset the episode and return the initial state."""
        self.current_step = 0
        self._state = np.random.randn(self.state_size).astype(np.float32)
        return self._state.copy()

    def step(self, action: int) -> tuple[np.ndarray, float, bool, dict[str, Any]]:
        """Advance the environment by one step."""
        self.current_step += 1
        clipped_action = int(np.clip(action, 0, self.action_size - 1))
        noise = np.random.randn(self.state_size).astype(np.float32) * 0.05
        action_signal = np.full(
            self.state_size,
            fill_value=(clipped_action + 1) / max(self.action_size, 1),
            dtype=np.float32,
        )
        next_state = (0.6 * self._state) + (0.4 * action_signal) + noise
        reward = float(
            self.reward_scale
            * (1.0 - np.mean(np.abs(next_state - action_signal)))
        )
        done = self.current_step >= self.max_steps
        self._state = next_state.astype(np.float32)
        return self._state.copy(), reward, bool(done), {"action": clipped_action}


class AgentTrainer:
    """Minimal trainer covering experience collection, training, and persistence."""

    def __init__(
        self,
        model: AgentLearningModel,
        config: dict[str, Any],
        env: TrainingEnvironment | None = None,
    ) -> None:
        self.model = model
        self.config = config
        self.env = env or TrainingEnvironment(
            state_size=config["state_size"],
            action_size=config["action_size"],
        )
        self.replay_buffer = ExperienceReplay(config.get("buffer_size", 100000))
        self.batch_size = config.get("batch_size", 32)
        self.update_freq = config.get("update_freq", 1)
        self.target_update_freq = config.get("target_update_freq", 100)
        self.episodes = config.get("episodes", 1)
        self.checkpoint_dir = Path(config.get("checkpoint_dir", "checkpoints"))
        self.episode_rewards: list[float] = []
        self.training_history: dict[str, list[Any]] = {
            "episode": [],
            "reward": [],
            "avg_loss": [],
            "epsilon": [],
        }
        self._training_steps = 0

    def collect_experience(
        self,
        num_steps: int,
        training: bool = True,
    ) -> tuple[float, int]:
        """Collect a fixed number of environment steps."""
        state = self.env.reset()
        total_reward = 0.0
        steps_taken = 0

        while steps_taken < num_steps:
            action = self.model.select_action(state, training=training)
            next_state, reward, done, _ = self.env.step(action)
            self.replay_buffer.add(state, action, reward, next_state, done)
            total_reward += float(reward)
            steps_taken += 1
            state = self.env.reset() if done else next_state

        return total_reward, steps_taken

    def train_on_batch(self) -> float:
        """Train the model on one replay batch."""
        if len(self.replay_buffer) < self.batch_size:
            return 0.0

        batch = self.replay_buffer.sample(self.batch_size)
        loss = float(self.model.train_step(*batch))
        self._training_steps += 1

        if (
            self.model.model_type == "dqn"
            and self._training_steps % self.target_update_freq == 0
        ):
            self.model.update_target_network()

        return loss

    def train_episode(self) -> dict[str, float]:
        """Run a single training episode."""
        state = self.env.reset()
        done = False
        total_reward = 0.0
        losses: list[float] = []
        steps = 0

        while not done:
            action = self.model.select_action(state, training=True)
            next_state, reward, done, _ = self.env.step(action)
            self.replay_buffer.add(state, action, reward, next_state, done)
            total_reward += float(reward)
            steps += 1

            if steps % self.update_freq == 0:
                batch_loss = self.train_on_batch()
                if batch_loss:
                    losses.append(batch_loss)

            state = next_state

        self.model.decay_epsilon()
        avg_loss = float(np.mean(losses)) if losses else 0.0
        metrics = {
            "reward": float(total_reward),
            "steps": float(steps),
            "avg_loss": avg_loss,
            "epsilon": float(self.model.epsilon),
        }
        self.episode_rewards.append(float(total_reward))
        self.training_history["episode"].append(len(self.episode_rewards) - 1)
        self.training_history["reward"].append(float(total_reward))
        self.training_history["avg_loss"].append(avg_loss)
        self.training_history["epsilon"].append(float(self.model.epsilon))
        return metrics

    def evaluate(self, num_episodes: int = 1) -> dict[str, float]:
        """Evaluate the model without exploration."""
        rewards: list[float] = []

        for _ in range(num_episodes):
            state = self.env.reset()
            done = False
            total_reward = 0.0

            while not done:
                action = self.model.select_action(state, training=False)
                state, reward, done, _ = self.env.step(action)
                total_reward += float(reward)

            rewards.append(float(total_reward))

        rewards_array = np.array(rewards, dtype=np.float32)
        return {
            "mean_reward": float(np.mean(rewards_array)),
            "std_reward": float(np.std(rewards_array)),
            "max_reward": float(np.max(rewards_array)),
            "min_reward": float(np.min(rewards_array)),
        }

    def save_checkpoint(self, episode: int, is_best: bool = False) -> None:
        """Save a training checkpoint."""
        self.checkpoint_dir.mkdir(parents=True, exist_ok=True)
        checkpoint_path = self.checkpoint_dir / f"model_episode_{episode}.h5"
        self.model.save_model(str(checkpoint_path))

        if is_best:
            self.model.save_model(str(self.checkpoint_dir / "best_model.h5"))

    def save_history(self, filepath: str) -> None:
        """Persist training history as JSON."""
        path = Path(filepath)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8") as history_file:
            json.dump(self.training_history, history_file)
