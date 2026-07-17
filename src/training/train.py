"""
Training utilities for AI-morphasis agents.

Provides a lightweight simulated :class:`TrainingEnvironment` and an
:class:`AgentTrainer` that orchestrates experience collection, batch
training, evaluation, and checkpointing.
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Tuple

import numpy as np

from src.models.neural_network import AgentLearningModel, ExperienceReplay

logger = logging.getLogger(__name__)


class TrainingEnvironment:
    """
    Minimal simulated environment for agent training and evaluation.

    Generates random Gaussian states and rewards.  Episodes terminate
    automatically after *max_steps* steps.

    Args:
        state_size: Dimension of the observation vector (must be > 0).
        action_size: Number of discrete actions (must be > 0).
        max_steps: Maximum number of steps per episode (must be > 0).
    """

    def __init__(self, state_size: int, action_size: int, max_steps: int = 500):
        if state_size <= 0:
            raise ValueError(f"state_size must be a positive integer, got {state_size}")
        if action_size <= 0:
            raise ValueError(f"action_size must be a positive integer, got {action_size}")
        if max_steps <= 0:
            raise ValueError(f"max_steps must be a positive integer, got {max_steps}")

        self.state_size = state_size
        self.action_size = action_size
        self.max_steps = max_steps
        self.current_step: int = 0
        self._state: np.ndarray = np.zeros(state_size, dtype=np.float32)

    def reset(self) -> np.ndarray:
        """
        Reset the environment to the start of a new episode.

        Returns:
            Initial state array of shape ``[state_size]``.
        """
        self.current_step = 0
        self._state = np.random.randn(self.state_size).astype(np.float32)
        return self._state.copy()

    def step(self, action: int) -> Tuple[np.ndarray, float, bool, Dict]:
        """
        Advance the environment by one step.

        Args:
            action: Integer action in ``[0, action_size)``.

        Returns:
            ``(next_state, reward, done, info)`` where *done* is ``True``
            once ``current_step >= max_steps``.
        """
        self.current_step += 1
        next_state = np.random.randn(self.state_size).astype(np.float32)
        reward = float(np.random.randn())
        done = self.current_step >= self.max_steps
        info: Dict = {"step": self.current_step, "action": int(action)}
        self._state = next_state
        return next_state.copy(), reward, done, info


class AgentTrainer:
    """
    Orchestrates DQN / policy-gradient agent training.

    Handles experience collection, replay-buffer management, batch
    training, periodic target-network updates, evaluation, and
    checkpoint / history persistence.

    Args:
        model: A fully initialised :class:`~src.models.neural_network.AgentLearningModel`.
        config: Training configuration dictionary.  Recognised keys:

            - ``buffer_size`` (int, default 100000)
            - ``batch_size`` (int, default 32)
            - ``update_freq`` (int, default 4) – gradient steps per N env steps
            - ``target_update_freq`` (int, default 1000) – hard target-network sync
            - ``episodes`` (int, default 200)
            - ``checkpoint_dir`` (str, default ``"checkpoints"``)
        env: A :class:`TrainingEnvironment` instance.
    """

    def __init__(
        self,
        model: AgentLearningModel,
        config: Dict,
        env: TrainingEnvironment,
    ):
        self.model = model
        self.config = config
        self.env = env

        self.replay_buffer = ExperienceReplay(
            max_size=config.get("buffer_size", 100000)
        )
        self.episode_rewards: List[float] = []
        self.training_history: Dict[str, List] = {
            "episode": [],
            "reward": [],
            "avg_loss": [],
            "epsilon": [],
            "steps": [],
        }
        self.checkpoint_dir = Path(config.get("checkpoint_dir", "checkpoints"))
        self._step_count: int = 0

        # Running env state for collect_experience across calls
        self._current_state: np.ndarray = self.env.reset()
        self._env_initialized: bool = True

    # ── Experience collection ────────────────────────────────────────────────

    def collect_experience(
        self, num_steps: int, training: bool = True
    ) -> Tuple[float, int]:
        """
        Run the agent in the environment for *num_steps* steps.

        Collected transitions are stored in the replay buffer.  Episode
        boundaries are handled transparently (environment is auto-reset).

        Args:
            num_steps: Number of environment steps to execute.
            training: Pass to :meth:`~AgentLearningModel.select_action`.

        Returns:
            ``(total_reward, steps)`` accumulated over all steps taken.
        """
        total_reward = 0.0
        steps = 0

        for _ in range(num_steps):
            action = self.model.select_action(self._current_state, training=training)
            next_state, reward, done, _ = self.env.step(action)
            self.replay_buffer.add(self._current_state, action, reward, next_state, done)
            total_reward += reward
            self._current_state = next_state
            steps += 1
            self._step_count += 1

            if done:
                self._current_state = self.env.reset()

        return total_reward, steps

    # ── Batch training ───────────────────────────────────────────────────────

    def train_on_batch(self) -> float:
        """
        Sample one mini-batch from the replay buffer and run a gradient step.

        Returns:
            Loss value, or ``0.0`` if the buffer has fewer entries than
            ``batch_size``.
        """
        batch_size = self.config.get("batch_size", 32)
        if len(self.replay_buffer) < batch_size:
            return 0.0

        states, actions, rewards, next_states, dones = self.replay_buffer.sample(batch_size)
        return self.model.train_step(states, actions, rewards, next_states, dones)

    # ── Episode training ─────────────────────────────────────────────────────

    def train_episode(self) -> Dict:
        """
        Run a single full training episode from reset to terminal.

        Performs gradient updates every ``update_freq`` steps and syncs
        the DQN target network every ``target_update_freq`` steps.

        Returns:
            Dictionary with keys ``reward``, ``steps``, ``avg_loss``, ``epsilon``.
        """
        state = self.env.reset()
        total_reward = 0.0
        episode_steps = 0
        losses: List[float] = []
        batch_size = self.config.get("batch_size", 32)
        update_freq = self.config.get("update_freq", 4)
        target_update_freq = self.config.get("target_update_freq", 1000)
        done = False

        while not done:
            action = self.model.select_action(state, training=True)
            next_state, reward, done, _ = self.env.step(action)
            self.replay_buffer.add(state, action, reward, next_state, done)
            state = next_state
            total_reward += reward
            episode_steps += 1
            self._step_count += 1

            if episode_steps % update_freq == 0 and len(self.replay_buffer) >= batch_size:
                loss = self.train_on_batch()
                losses.append(loss)

            if self._step_count % target_update_freq == 0:
                self.model.update_target_network()

        self.model.decay_epsilon()

        metrics = {
            "reward": total_reward,
            "steps": episode_steps,
            "avg_loss": float(np.mean(losses)) if losses else 0.0,
            "epsilon": self.model.epsilon,
        }
        self.episode_rewards.append(total_reward)
        return metrics

    # ── Evaluation ───────────────────────────────────────────────────────────

    def evaluate(self, num_episodes: int = 5) -> Dict:
        """
        Evaluate the current policy greedily for *num_episodes* episodes.

        Args:
            num_episodes: Number of evaluation episodes.

        Returns:
            Dictionary with keys ``mean_reward``, ``std_reward``,
            ``max_reward``, ``min_reward``.
        """
        rewards: List[float] = []
        for _ in range(num_episodes):
            state = self.env.reset()
            episode_reward = 0.0
            done = False
            while not done:
                action = self.model.select_action(state, training=False)
                state, reward, done, _ = self.env.step(action)
                episode_reward += reward
            rewards.append(episode_reward)

        return {
            "mean_reward": float(np.mean(rewards)),
            "std_reward": float(np.std(rewards)),
            "max_reward": float(np.max(rewards)),
            "min_reward": float(np.min(rewards)),
        }

    # ── Persistence ──────────────────────────────────────────────────────────

    def save_checkpoint(self, episode: int, is_best: bool = False) -> None:
        """
        Save a model checkpoint for the given episode.

        Args:
            episode: Episode index used in the filename.
            is_best: If ``True``, also saves a ``best_model.h5`` copy.
        """
        self.checkpoint_dir.mkdir(parents=True, exist_ok=True)
        filepath = str(self.checkpoint_dir / f"model_episode_{episode}.h5")
        self.model.save_model(filepath)
        logger.info("Checkpoint saved: %s", filepath)

        if is_best:
            best_path = str(self.checkpoint_dir / "best_model.h5")
            self.model.save_model(best_path)
            logger.info("Best model updated: %s", best_path)

    def save_history(self, filepath: str) -> None:
        """
        Persist training history to a JSON file.

        Args:
            filepath: Destination path (e.g. ``"results/history.json"``).
        """
        with open(filepath, "w") as fh:
            json.dump(self.training_history, fh, indent=2)
        logger.info("Training history saved to %s", filepath)
