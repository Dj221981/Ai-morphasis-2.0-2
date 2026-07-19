"""
Training module for AI-morphasis Agent Learning System.

Implements TrainingEnvironment and AgentTrainer for reinforcement learning workflows.
"""

import json
import logging
import numpy as np
from pathlib import Path
from typing import Dict, Any, Optional, Tuple

logger = logging.getLogger(__name__)


class TrainingEnvironment:
    """
    Simulated training environment for RL agents.

    Provides a simple configurable environment with state/action spaces
    and episode management.
    """

    def __init__(
        self,
        state_size: int = 32,
        action_size: int = 8,
        max_steps: int = 200,
        reward_scale: float = 1.0,
    ):
        """
        Initialize training environment.

        Args:
            state_size: Dimension of state space
            action_size: Number of possible actions
            max_steps: Maximum steps per episode before forced termination
            reward_scale: Scale factor applied to rewards
        """
        self.state_size = state_size
        self.action_size = action_size
        self.max_steps = max_steps
        self.reward_scale = reward_scale

        self.current_step = 0
        self._state: Optional[np.ndarray] = None

    def reset(self) -> np.ndarray:
        """
        Reset the environment to an initial state.

        Returns:
            Initial state observation
        """
        self.current_step = 0
        self._state = np.random.randn(self.state_size).astype(np.float32)
        return self._state.copy()

    def step(self, action: int) -> Tuple[np.ndarray, float, bool, Dict[str, Any]]:
        """
        Take a step in the environment.

        Args:
            action: Action index to execute

        Returns:
            Tuple of (next_state, reward, done, info)
        """
        if self._state is None:
            self._state = np.random.randn(self.state_size).astype(np.float32)

        self.current_step += 1

        # Transition: add action-dependent noise to current state
        action_effect = np.zeros(self.state_size, dtype=np.float32)
        action_effect[action % self.state_size] = 0.1
        self._state = (
            0.95 * self._state
            + action_effect
            + 0.05 * np.random.randn(self.state_size).astype(np.float32)
        )

        # Reward: negative L2 norm encourages state toward origin
        reward = float(-np.linalg.norm(self._state) * self.reward_scale)

        # Episode ends at max_steps or with small probability
        done = self.current_step >= self.max_steps or (
            np.random.random() < 0.01
        )

        info: Dict[str, Any] = {
            "step": self.current_step,
            "action": action,
        }

        return self._state.copy(), reward, done, info


class AgentTrainer:
    """
    Trainer that manages the full RL training loop.

    Coordinates experience collection, network updates, and checkpointing
    for an AgentLearningModel.
    """

    def __init__(
        self,
        model: Any,
        config: Dict[str, Any],
        env: Optional[TrainingEnvironment] = None,
    ):
        """
        Initialize Agent Trainer.

        Args:
            model: An AgentLearningModel instance
            config: Training configuration dictionary
            env: Training environment (created from config if not provided)
        """
        from src.models.neural_network import ExperienceReplay

        self.model = model
        self.config = config

        state_size = config.get("state_size", 32)
        action_size = config.get("action_size", 8)

        self.env = env or TrainingEnvironment(
            state_size=state_size,
            action_size=action_size,
        )

        buffer_size = config.get("buffer_size", 100000)
        self.replay_buffer = ExperienceReplay(max_size=buffer_size)

        self.batch_size: int = config.get("batch_size", 32)
        self.update_freq: int = config.get("update_freq", 4)
        self.target_update_freq: int = config.get("target_update_freq", 1000)
        self.checkpoint_dir = Path(config.get("checkpoint_dir", "/models/checkpoints"))

        self.episode_rewards = []
        self.total_steps = 0

        self.training_history: Dict[str, list] = {
            "episode": [],
            "reward": [],
            "steps": [],
            "avg_loss": [],
            "epsilon": [],
        }

    def collect_experience(
        self, num_steps: int = 1, training: bool = True
    ) -> Tuple[float, int]:
        """
        Run the environment for a fixed number of steps and store transitions.

        Args:
            num_steps: Number of environment steps to collect
            training: Whether to use exploration (epsilon-greedy)

        Returns:
            Tuple of (total_reward, steps_taken)
        """
        if self.env._state is None:
            self.env.reset()

        total_reward = 0.0
        steps = 0

        for _ in range(num_steps):
            state = self.env._state.copy()
            action = self.model.select_action(state, training=training)
            next_state, reward, done, _ = self.env.step(action)

            self.replay_buffer.add(state, action, reward, next_state, done)

            total_reward += reward
            steps += 1
            self.total_steps += 1

            if done:
                self.env.reset()

        return total_reward, steps

    def train_on_batch(self) -> float:
        """
        Sample a mini-batch from the replay buffer and update the model.

        Returns:
            Loss value (0.0 if buffer is too small)
        """
        if len(self.replay_buffer) < self.batch_size:
            return 0.0

        states, actions, rewards, next_states, dones = self.replay_buffer.sample(
            self.batch_size
        )
        loss = self.model.train_step(states, actions, rewards, next_states, dones)
        return float(loss)

    def train_episode(self) -> Dict[str, Any]:
        """
        Run a full episode of data collection and learning.

        Returns:
            Dictionary with episode metrics
        """
        state = self.env.reset()
        done = False
        episode_reward = 0.0
        episode_steps = 0
        losses = []

        while not done:
            action = self.model.select_action(state, training=True)
            next_state, reward, done, _ = self.env.step(action)

            self.replay_buffer.add(state, action, reward, next_state, done)

            episode_reward += reward
            episode_steps += 1
            self.total_steps += 1

            if (
                self.total_steps % self.update_freq == 0
                and len(self.replay_buffer) >= self.batch_size
            ):
                loss = self.train_on_batch()
                losses.append(loss)

            if (
                self.total_steps % self.target_update_freq == 0
                and self.model.model_type == "dqn"
            ):
                self.model.update_target_network()

            state = next_state

        self.model.decay_epsilon()
        self.episode_rewards.append(episode_reward)

        avg_loss = float(np.mean(losses)) if losses else 0.0
        metrics = {
            "reward": episode_reward,
            "steps": episode_steps,
            "avg_loss": avg_loss,
            "epsilon": self.model.epsilon,
        }

        episode_idx = len(self.training_history["episode"])
        for key in ["episode", "reward", "steps", "avg_loss", "epsilon"]:
            self.training_history[key].append(
                episode_idx if key == "episode" else metrics[key]
            )

        return metrics

    def evaluate(self, num_episodes: int = 5) -> Dict[str, float]:
        """
        Evaluate the model over several episodes without exploration.

        Args:
            num_episodes: Number of evaluation episodes

        Returns:
            Dictionary with evaluation statistics
        """
        rewards = []

        for _ in range(num_episodes):
            state = self.env.reset()
            done = False
            episode_reward = 0.0

            while not done:
                action = self.model.select_action(state, training=False)
                state, reward, done, _ = self.env.step(action)
                episode_reward += reward

            rewards.append(episode_reward)

        rewards_arr = np.array(rewards)
        return {
            "mean_reward": float(np.mean(rewards_arr)),
            "std_reward": float(np.std(rewards_arr)),
            "max_reward": float(np.max(rewards_arr)),
            "min_reward": float(np.min(rewards_arr)),
        }

    def save_checkpoint(self, episode: int, is_best: bool = False) -> None:
        """
        Save a model checkpoint.

        Args:
            episode: Current episode number
            is_best: Whether this is the best model so far
        """
        self.checkpoint_dir.mkdir(parents=True, exist_ok=True)
        filepath = str(self.checkpoint_dir / f"model_episode_{episode}.h5")
        self.model.save_model(filepath)

        if is_best:
            best_path = str(self.checkpoint_dir / "best_model.h5")
            self.model.save_model(best_path)

        logger.info(f"Checkpoint saved: {filepath}")

    def save_history(self, filepath: str) -> None:
        """
        Save training history to a JSON file.

        Args:
            filepath: Destination file path
        """
        with open(filepath, "w") as f:
            json.dump(self.training_history, f, indent=2)

        logger.info(f"Training history saved to {filepath}")
