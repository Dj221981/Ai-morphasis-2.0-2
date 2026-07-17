"""
Neural Network Model for AI-morphasis Agent Learning System

This module implements deep learning models using TensorFlow/Keras for training
adaptive agents with reinforcement learning capabilities.

Supports two modes:
- ``dqn``: Deep Q-Network with a separate target network and epsilon-greedy exploration.
- ``policy_gradient``: Advantage Actor-Critic (A2C) with a shared PolicyNetwork.
"""

import json
import logging
from pathlib import Path
from typing import List, Tuple

import numpy as np
import tensorflow as tf
from tensorflow import keras
from tensorflow.keras import layers, Model
from tensorflow.keras.optimizers import Adam
from tensorflow.keras.losses import Huber

# Configure logging
logger = logging.getLogger(__name__)

# Supported configuration constants
_VALID_MODEL_TYPES = {"dqn", "policy_gradient"}
_VALID_DEVICES = {"cpu", "gpu"}
_VALID_ACTION_SPACES = {"discrete", "continuous"}

# A2C hyper-parameters (policy gradient)
_VALUE_LOSS_COEF = 0.5
_ENTROPY_COEF = 0.01


class DQNNetwork(Model):
    """
    Deep Q-Network (DQN) for agent decision-making and learning.

    Estimates action values (Q-values) for reinforcement learning.
    Each hidden block consists of a Dense layer, BatchNormalization, and Dropout.

    Args:
        state_size: Dimension of the input state vector (must be > 0).
        action_size: Number of discrete actions (must be > 0).
        hidden_layers: Sizes of hidden layers (default: ``[128, 64]``).
        activation: Activation function for hidden Dense layers.
        name: Keras model name.
    """

    def __init__(
        self,
        state_size: int,
        action_size: int,
        hidden_layers: List[int] = None,
        activation: str = "relu",
        name: str = "dqn_network",
    ):
        if state_size <= 0:
            raise ValueError(f"state_size must be a positive integer, got {state_size}")
        if action_size <= 0:
            raise ValueError(f"action_size must be a positive integer, got {action_size}")

        hidden_layers = list(hidden_layers) if hidden_layers is not None else [128, 64]
        if not hidden_layers or any(u <= 0 for u in hidden_layers):
            raise ValueError("hidden_layers must be a non-empty list of positive integers")

        super(DQNNetwork, self).__init__(name=name)

        self.state_size = state_size
        self.action_size = action_size
        self.activation = activation

        # Build network layers.  Using individual named attributes in a list is
        # sufficient for Keras weight tracking in TF/Keras subclassed models.
        self.dense_layers: List[layers.Layer] = []
        for units in hidden_layers:
            self.dense_layers.append(layers.Dense(units, activation=activation))
            self.dense_layers.append(layers.BatchNormalization())
            self.dense_layers.append(layers.Dropout(0.2))

        # Output Q-value layer (one logit per action, no activation)
        self.output_layer = layers.Dense(action_size, activation=None)

        logger.info(
            "DQN Network initialized: state_size=%d, action_size=%d, hidden_layers=%s",
            state_size,
            action_size,
            hidden_layers,
        )

    def call(self, states: tf.Tensor, training: bool = False) -> tf.Tensor:
        """
        Forward pass through the network.

        Args:
            states: Float32 tensor of shape ``[batch_size, state_size]``.
            training: Pass ``True`` during gradient updates (enables Dropout /
                BatchNorm training behaviour).

        Returns:
            Q-value tensor of shape ``[batch_size, action_size]``.
        """
        x = states
        for layer in self.dense_layers:
            if isinstance(layer, (layers.Dropout, layers.BatchNormalization)):
                x = layer(x, training=training)
            else:
                x = layer(x)
        return self.output_layer(x)


class PolicyNetwork(Model):
    """
    Actor-Critic Policy Network for policy-gradient learning (A2C).

    Outputs both a policy distribution and a state-value estimate from shared
    hidden layers.

    Args:
        state_size: Dimension of the input state vector (must be > 0).
        action_size: Number of actions / action dimension (must be > 0).
        hidden_layers: Sizes of shared hidden layers (default: ``[128, 64]``).
        action_space: ``"discrete"`` (softmax policy) or ``"continuous"``
            (Gaussian mean + log-std policy).
        name: Keras model name.
    """

    def __init__(
        self,
        state_size: int,
        action_size: int,
        hidden_layers: List[int] = None,
        action_space: str = "discrete",
        name: str = "policy_network",
    ):
        if state_size <= 0:
            raise ValueError(f"state_size must be a positive integer, got {state_size}")
        if action_size <= 0:
            raise ValueError(f"action_size must be a positive integer, got {action_size}")
        if action_space not in _VALID_ACTION_SPACES:
            raise ValueError(f"action_space must be one of {_VALID_ACTION_SPACES}, got '{action_space}'")

        hidden_layers = list(hidden_layers) if hidden_layers is not None else [128, 64]
        if not hidden_layers or any(u <= 0 for u in hidden_layers):
            raise ValueError("hidden_layers must be a non-empty list of positive integers")

        super(PolicyNetwork, self).__init__(name=name)

        self.state_size = state_size
        self.action_size = action_size
        self.action_space = action_space

        # Shared representation layers
        self.shared_layers: List[layers.Layer] = [
            layers.Dense(units, activation="relu") for units in hidden_layers
        ]

        # Policy head
        if action_space == "discrete":
            self.policy_head = layers.Dense(action_size, activation="softmax")
        else:
            # Continuous: separate mean and log-std heads
            self.mean_head = layers.Dense(action_size, activation="tanh")
            self.log_std_head = layers.Dense(action_size, activation=None)

        # Value head (critic)
        self.value_head = layers.Dense(1, activation=None)

        logger.info(
            "Policy Network initialized: state_size=%d, action_size=%d, action_space=%s",
            state_size,
            action_size,
            action_space,
        )

    def call(self, states: tf.Tensor, training: bool = False) -> Tuple[tf.Tensor, tf.Tensor]:
        """
        Forward pass returning policy distribution and value estimate.

        Args:
            states: Float32 tensor of shape ``[batch_size, state_size]``.
            training: Pass ``True`` during gradient updates.

        Returns:
            ``(policy_output, value_estimate)`` where:

            - For ``discrete``: ``policy_output`` has shape
              ``[batch_size, action_size]`` (softmax probabilities).
            - For ``continuous``: ``policy_output`` has shape
              ``[batch_size, 2 * action_size]`` (mean ‖ log_std).
            - ``value_estimate`` has shape ``[batch_size, 1]``.
        """
        x = states
        for layer in self.shared_layers:
            x = layer(x, training=training)

        if self.action_space == "discrete":
            policy = self.policy_head(x)
        else:
            mean = self.mean_head(x)
            log_std = self.log_std_head(x)
            policy = tf.concat([mean, log_std], axis=-1)

        value = self.value_head(x)
        return policy, value


class AgentLearningModel:
    """
    Production-ready learning model for AI-morphasis agents.

    Wraps either a :class:`DQNNetwork` (``model_type="dqn"``) or a
    :class:`PolicyNetwork` (``model_type="policy_gradient"``).  Both modes
    share the same :meth:`select_action` / :meth:`train_step` interface so
    callers do not need to branch on the algorithm.

    DQN uses:
        - Epsilon-greedy exploration
        - Huber loss with a frozen target network
        - Hard target-network updates via :meth:`update_target_network`

    Policy gradient uses:
        - Softmax sampling during training, argmax during evaluation
        - Advantage Actor-Critic (A2C) loss (policy gradient + value baseline)

    Args:
        state_size: Dimension of the state vector (must be > 0).
        action_size: Number of discrete actions (must be > 0).
        learning_rate: Adam learning rate (must be > 0).
        gamma: Discount factor in ``[0, 1]``.
        epsilon: Initial epsilon for epsilon-greedy (``model_type="dqn"`` only).
        epsilon_decay: Multiplicative decay applied per call to
            :meth:`decay_epsilon` (must be in ``(0, 1]``).
        epsilon_min: Lower bound for epsilon (must be in ``[0, epsilon]``).
        model_type: ``"dqn"`` or ``"policy_gradient"``.
        device: ``"cpu"`` or ``"gpu"``.
    """

    def __init__(
        self,
        state_size: int,
        action_size: int,
        learning_rate: float = 0.001,
        gamma: float = 0.99,
        epsilon: float = 1.0,
        epsilon_decay: float = 0.995,
        epsilon_min: float = 0.01,
        model_type: str = "dqn",
        device: str = "cpu",
    ):
        # ── Validate constructor arguments ──────────────────────────────────
        if state_size <= 0:
            raise ValueError(f"state_size must be a positive integer, got {state_size}")
        if action_size <= 0:
            raise ValueError(f"action_size must be a positive integer, got {action_size}")
        if learning_rate <= 0:
            raise ValueError(f"learning_rate must be positive, got {learning_rate}")
        if not (0.0 <= gamma <= 1.0):
            raise ValueError(f"gamma must be in [0, 1], got {gamma}")
        if not (0.0 <= epsilon <= 1.0):
            raise ValueError(f"epsilon must be in [0, 1], got {epsilon}")
        if not (0.0 < epsilon_decay <= 1.0):
            raise ValueError(f"epsilon_decay must be in (0, 1], got {epsilon_decay}")
        if not (0.0 <= epsilon_min <= epsilon):
            raise ValueError(
                f"epsilon_min must be in [0, epsilon={epsilon}], got {epsilon_min}"
            )
        if model_type not in _VALID_MODEL_TYPES:
            raise ValueError(
                f"model_type must be one of {_VALID_MODEL_TYPES}, got '{model_type}'"
            )
        if device not in _VALID_DEVICES:
            raise ValueError(f"device must be one of {_VALID_DEVICES}, got '{device}'")

        self.state_size = state_size
        self.action_size = action_size
        self.learning_rate = learning_rate
        self.gamma = gamma
        self.epsilon = epsilon
        self.epsilon_decay = epsilon_decay
        self.epsilon_min = epsilon_min
        self.model_type = model_type
        self.device = device

        # ── Device selection ────────────────────────────────────────────────
        if device == "gpu" and tf.config.list_physical_devices("GPU"):
            self.device_name = "/GPU:0"
            logger.info("Using GPU for training")
        else:
            self.device_name = "/CPU:0"
            logger.info("Using CPU for training")

        # ── Network initialisation ──────────────────────────────────────────
        # A dummy forward pass is performed immediately so that all layer
        # weights are created before we attempt to copy them to the target
        # network.
        dummy_input = tf.zeros([1, state_size], dtype=tf.float32)

        if model_type == "dqn":
            self.network = DQNNetwork(state_size, action_size)
            self.target_network = DQNNetwork(state_size, action_size, name="target_dqn_network")
            # Build both networks before copying weights
            self.network(dummy_input, training=False)
            self.target_network(dummy_input, training=False)
            self.target_network.set_weights(self.network.get_weights())
        else:
            self.network = PolicyNetwork(state_size, action_size)
            self.network(dummy_input, training=False)

        # ── Optimiser (gradient clipping for stability) ─────────────────────
        self.optimizer = Adam(learning_rate=learning_rate, clipnorm=1.0)

        # DQN Huber loss is applied per element; A2C uses custom loss logic.
        self.loss_fn = Huber()

        # Metrics
        self.train_loss = keras.metrics.Mean(name="train_loss")

        logger.info(
            "AgentLearningModel initialized: model_type=%s, state_size=%d, "
            "action_size=%d, learning_rate=%g",
            model_type,
            state_size,
            action_size,
            learning_rate,
        )

    # ── Action selection ─────────────────────────────────────────────────────

    def select_action(self, state: np.ndarray, training: bool = True) -> int:
        """
        Select an action for the given state.

        For DQN:
            Uses epsilon-greedy: random with probability ``epsilon`` (when
            ``training=True``), greedy otherwise.

        For policy_gradient (discrete):
            Samples from the softmax distribution during training; uses argmax
            during evaluation.

        Args:
            state: 1-D float array of shape ``[state_size]``.
            training: Whether the agent is in training mode.

        Returns:
            Action index in ``[0, action_size)``.

        Raises:
            ValueError: If ``state`` has an unexpected shape.
        """
        state = np.asarray(state, dtype=np.float32)
        if state.ndim != 1 or state.shape[0] != self.state_size:
            raise ValueError(
                f"Expected state of shape ({self.state_size},), got {state.shape}"
            )

        if self.model_type == "dqn":
            if training and np.random.random() < self.epsilon:
                return int(np.random.randint(0, self.action_size))
            state_tensor = tf.convert_to_tensor([state], dtype=tf.float32)
            q_values = self.network(state_tensor, training=False)
            return int(np.argmax(q_values.numpy()[0]))

        # policy_gradient – discrete action space only in the base model
        state_tensor = tf.convert_to_tensor([state], dtype=tf.float32)
        policy_probs, _ = self.network(state_tensor, training=False)
        if training:
            log_probs = tf.math.log(tf.clip_by_value(policy_probs, 1e-8, 1.0))
            action = tf.random.categorical(log_probs, num_samples=1)
            return int(action.numpy()[0][0])
        return int(tf.argmax(policy_probs[0]).numpy())

    # ── Training ─────────────────────────────────────────────────────────────

    def train_step(
        self,
        states: np.ndarray,
        actions: np.ndarray,
        rewards: np.ndarray,
        next_states: np.ndarray,
        dones: np.ndarray,
    ) -> float:
        """
        Perform one gradient-update step on a batch of experiences.

        DQN:
            Minimises Huber loss between current Q-values and one-step
            Bellman targets computed from the frozen target network.

        Policy gradient (A2C):
            Minimises ``policy_loss + value_coef * value_loss - entropy_coef * entropy``.

        Args:
            states: Float32 array of shape ``[batch_size, state_size]``.
            actions: Int array of shape ``[batch_size]``.
                Values must be in ``[0, action_size)``.
            rewards: Float32 array of shape ``[batch_size]``.
            next_states: Float32 array of shape ``[batch_size, state_size]``.
            dones: Float32 / bool array of shape ``[batch_size]`` (1 = terminal).

        Returns:
            Scalar loss value for this batch.

        Raises:
            ValueError: If any input has an unexpected shape or invalid values.
        """
        states = np.asarray(states, dtype=np.float32)
        actions = np.asarray(actions, dtype=np.int32)
        rewards = np.asarray(rewards, dtype=np.float32)
        next_states = np.asarray(next_states, dtype=np.float32)
        dones = np.asarray(dones, dtype=np.float32)

        batch_size = states.shape[0]
        if states.shape != (batch_size, self.state_size):
            raise ValueError(
                f"states must have shape (batch_size, {self.state_size}), got {states.shape}"
            )
        if next_states.shape != (batch_size, self.state_size):
            raise ValueError(
                f"next_states must have shape (batch_size, {self.state_size}), "
                f"got {next_states.shape}"
            )
        if actions.shape != (batch_size,):
            raise ValueError(f"actions must have shape (batch_size,), got {actions.shape}")
        if np.any(actions < 0) or np.any(actions >= self.action_size):
            raise ValueError(
                f"actions must be in [0, {self.action_size}), "
                f"got min={actions.min()}, max={actions.max()}"
            )

        with tf.device(self.device_name):
            states_t = tf.convert_to_tensor(states)
            actions_t = tf.convert_to_tensor(actions)
            rewards_t = tf.convert_to_tensor(rewards)
            next_states_t = tf.convert_to_tensor(next_states)
            dones_t = tf.convert_to_tensor(dones)

            if self.model_type == "dqn":
                loss = self._train_step_dqn(states_t, actions_t, rewards_t, next_states_t, dones_t)
            else:
                loss = self._train_step_policy(states_t, actions_t, rewards_t, next_states_t, dones_t)

        self.train_loss.update_state(loss)

        loss_val = float(loss.numpy())
        if not np.isfinite(loss_val):
            logger.warning("Non-finite loss detected: %s", loss_val)
        return loss_val

    def _train_step_dqn(
        self,
        states: tf.Tensor,
        actions: tf.Tensor,
        rewards: tf.Tensor,
        next_states: tf.Tensor,
        dones: tf.Tensor,
    ) -> tf.Tensor:
        """DQN Bellman update (Huber loss on Q-value residuals)."""
        with tf.GradientTape() as tape:
            q_values = self.network(states, training=True)

            batch_indices = tf.range(tf.shape(q_values)[0])
            action_indices = tf.stack([batch_indices, actions], axis=1)
            current_q = tf.gather_nd(q_values, action_indices)

            next_q_values = self.target_network(next_states, training=False)
            max_next_q = tf.reduce_max(next_q_values, axis=1)
            target_q = rewards + self.gamma * max_next_q * (1.0 - dones)

            loss = self.loss_fn(target_q, current_q)

        gradients = tape.gradient(loss, self.network.trainable_weights)
        grad_pairs = [
            (g, w)
            for g, w in zip(gradients, self.network.trainable_weights)
            if g is not None
        ]
        self.optimizer.apply_gradients(grad_pairs)
        return loss

    def _train_step_policy(
        self,
        states: tf.Tensor,
        actions: tf.Tensor,
        rewards: tf.Tensor,
        next_states: tf.Tensor,
        dones: tf.Tensor,
    ) -> tf.Tensor:
        """A2C policy-gradient update (policy loss + value loss + entropy bonus)."""
        with tf.GradientTape() as tape:
            policy_probs, values = self.network(states, training=True)
            _, next_values = self.network(next_states, training=False)

            values = tf.squeeze(values, axis=1)
            next_values = tf.squeeze(next_values, axis=1)

            # TD targets and advantages
            td_targets = rewards + self.gamma * next_values * (1.0 - dones)
            advantages = tf.stop_gradient(td_targets - values)

            # Policy loss
            batch_size = tf.shape(actions)[0]
            action_indices = tf.stack([tf.range(batch_size), actions], axis=1)
            selected_probs = tf.gather_nd(policy_probs, action_indices)
            log_probs = tf.math.log(tf.clip_by_value(selected_probs, 1e-8, 1.0))
            policy_loss = -tf.reduce_mean(log_probs * advantages)

            # Value loss (MSE on TD targets)
            value_loss = tf.reduce_mean(tf.square(td_targets - values))

            # Entropy bonus (encourages exploration)
            entropy = -tf.reduce_mean(
                tf.reduce_sum(
                    policy_probs * tf.math.log(tf.clip_by_value(policy_probs, 1e-8, 1.0)),
                    axis=1,
                )
            )

            loss = policy_loss + _VALUE_LOSS_COEF * value_loss - _ENTROPY_COEF * entropy

        gradients = tape.gradient(loss, self.network.trainable_weights)
        grad_pairs = [
            (g, w)
            for g, w in zip(gradients, self.network.trainable_weights)
            if g is not None
        ]
        self.optimizer.apply_gradients(grad_pairs)
        return loss

    # ── Target network & exploration ─────────────────────────────────────────

    def update_target_network(self) -> None:
        """Hard-copy main network weights to the target network (DQN only)."""
        if self.model_type == "dqn":
            self.target_network.set_weights(self.network.get_weights())
            logger.debug("Target network updated")

    def decay_epsilon(self) -> None:
        """Apply one epsilon-decay step, clamped to ``epsilon_min``."""
        if self.epsilon > self.epsilon_min:
            self.epsilon = max(self.epsilon * self.epsilon_decay, self.epsilon_min)

    # ── Introspection ────────────────────────────────────────────────────────

    def get_model_summary(self) -> str:
        """
        Return the Keras model architecture as a formatted string.

        Performs a real forward pass to ensure all sub-layers are built.

        Returns:
            Multi-line string produced by ``model.summary()``.
        """
        dummy_input = tf.zeros([1, self.state_size], dtype=tf.float32)
        self.network(dummy_input, training=False)

        summary_lines: List[str] = []
        self.network.summary(print_fn=summary_lines.append)
        return "\n".join(summary_lines)

    # ── Serialisation ────────────────────────────────────────────────────────

    def save_model(self, filepath: str) -> None:
        """
        Persist the model to disk.

        Saves network weights to *filepath* using HDF5 and stores training
        metadata (epsilon, step counters, etc.) to ``<filepath>.meta.json``
        alongside it.  The caller controls the filename and extension.

        Args:
            filepath: Destination path for the weights file (e.g.
                ``"checkpoints/model.h5"``).
        """
        import h5py  # bundled with TensorFlow/Keras

        filepath = str(filepath)
        # Ensure network is built before serialising
        dummy_input = tf.zeros([1, self.state_size], dtype=tf.float32)
        self.network(dummy_input, training=False)

        weights = self.network.get_weights()
        with h5py.File(filepath, "w") as hf:
            hf.attrs["num_weights"] = len(weights)
            for i, w in enumerate(weights):
                hf.create_dataset(f"weight_{i}", data=w)

        # Persist training state alongside the weights
        meta = {
            "model_type": self.model_type,
            "state_size": self.state_size,
            "action_size": self.action_size,
            "learning_rate": self.learning_rate,
            "gamma": self.gamma,
            "epsilon": self.epsilon,
            "epsilon_decay": self.epsilon_decay,
            "epsilon_min": self.epsilon_min,
        }
        meta_path = filepath + ".meta.json"
        with open(meta_path, "w") as fh:
            json.dump(meta, fh, indent=2)

        logger.info("Model saved to %s (metadata: %s)", filepath, meta_path)

    def load_model(self, filepath: str) -> None:
        """
        Restore model weights and training state from disk.

        The network is built via a dummy forward pass before weights are
        loaded so that the weight shapes match regardless of whether the
        network has been called previously.

        Args:
            filepath: Path to the weights file previously written by
                :meth:`save_model`.

        Raises:
            FileNotFoundError: If *filepath* does not exist.
        """
        import h5py  # bundled with TensorFlow/Keras

        filepath = str(filepath)
        if not Path(filepath).exists():
            raise FileNotFoundError(f"Model weights file not found: {filepath}")

        # Build the network first to ensure layer variables exist
        dummy_input = tf.zeros([1, self.state_size], dtype=tf.float32)
        self.network(dummy_input, training=False)

        with h5py.File(filepath, "r") as hf:
            num_weights = int(hf.attrs["num_weights"])
            weights = [hf[f"weight_{i}"][:] for i in range(num_weights)]
        self.network.set_weights(weights)

        if self.model_type == "dqn":
            self.target_network(dummy_input, training=False)
            self.target_network.set_weights(self.network.get_weights())

        # Restore training metadata if present
        meta_path = filepath + ".meta.json"
        if Path(meta_path).exists():
            with open(meta_path) as fh:
                meta = json.load(fh)
            self.epsilon = float(meta.get("epsilon", self.epsilon))
            logger.info("Training metadata restored from %s", meta_path)

        logger.info("Model loaded from %s", filepath)


class ExperienceReplay:
    """
    Ring-buffer experience replay for off-policy reinforcement learning.

    Experiences are stored as ``(state, action, reward, next_state, done)``
    tuples and overwrite the oldest entries once the buffer is full.

    Args:
        max_size: Maximum number of transitions to store (must be > 0).
    """

    def __init__(self, max_size: int = 100000):
        if max_size <= 0:
            raise ValueError(f"max_size must be a positive integer, got {max_size}")

        self.max_size = max_size
        self.buffer: list = []
        self.position: int = 0

    def add(
        self,
        state: np.ndarray,
        action: int,
        reward: float,
        next_state: np.ndarray,
        done: bool,
    ) -> None:
        """
        Add a transition to the replay buffer.

        Args:
            state: Current state array.
            action: Integer action index.
            reward: Scalar reward.
            next_state: Next state array.
            done: ``True`` if the episode terminated after this transition.
        """
        experience = (state, action, reward, next_state, done)

        if len(self.buffer) < self.max_size:
            self.buffer.append(experience)
        else:
            self.buffer[self.position] = experience

        self.position = (self.position + 1) % self.max_size

    def sample(
        self, batch_size: int
    ) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
        """
        Sample a random batch of transitions without replacement.

        Args:
            batch_size: Number of transitions to sample.  Must satisfy
                ``0 < batch_size <= len(buffer)``.

        Returns:
            Five arrays ``(states, actions, rewards, next_states, dones)``,
            each with a leading dimension equal to *batch_size*.

        Raises:
            ValueError: If the buffer is empty or *batch_size* is invalid.
        """
        if batch_size <= 0:
            raise ValueError(f"batch_size must be a positive integer, got {batch_size}")
        if len(self.buffer) == 0:
            raise ValueError("Cannot sample from an empty replay buffer")
        if batch_size > len(self.buffer):
            logger.warning(
                "Requested batch_size=%d exceeds buffer size=%d; "
                "sampling all available experiences.",
                batch_size,
                len(self.buffer),
            )
            batch_size = len(self.buffer)

        indices = np.random.choice(len(self.buffer), batch_size, replace=False)
        experiences = [self.buffer[i] for i in indices]

        states = np.array([e[0] for e in experiences], dtype=np.float32)
        actions = np.array([e[1] for e in experiences], dtype=np.int32)
        rewards = np.array([e[2] for e in experiences], dtype=np.float32)
        next_states = np.array([e[3] for e in experiences], dtype=np.float32)
        dones = np.array([e[4] for e in experiences], dtype=np.float32)

        return states, actions, rewards, next_states, dones

    def __len__(self) -> int:
        """Current number of transitions in the buffer."""
        return len(self.buffer)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    logger.info("Creating example agent learning model...")

    model = AgentLearningModel(
        state_size=64,
        action_size=10,
        learning_rate=0.001,
        model_type="dqn",
        device="cpu",
    )

    replay = ExperienceReplay(max_size=10000)

    for _ in range(100):
        state = np.random.randn(64).astype(np.float32)
        action = model.select_action(state)
        reward = float(np.random.randn())
        next_state = np.random.randn(64).astype(np.float32)
        done = bool(np.random.random() > 0.9)
        replay.add(state, action, reward, next_state, done)

    if len(replay) >= 32:
        s, a, r, ns, d = replay.sample(32)
        loss = model.train_step(s, a, r, ns, d)
        logger.info("Training loss: %f", loss)

    logger.info("Example training completed successfully!")
